from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from psycopg.rows import dict_row
import psycopg
import os

from execution_api import ALLOWED_TESTS, run_test

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])
DB = os.environ["DATABASE_URL"]


class CampaignRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    test_ids: list[str] = Field(min_length=1, max_length=20)


def initialize_campaign_database():
    with psycopg.connect(DB) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_campaigns (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'RUNNING',
                total_tests INTEGER NOT NULL,
                passed INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT now(),
                completed_at TIMESTAMPTZ
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS campaign_executions (
                campaign_id BIGINT NOT NULL
                    REFERENCES test_campaigns(id),
                execution_id BIGINT NOT NULL
                    REFERENCES test_executions(id),
                PRIMARY KEY (campaign_id, execution_id)
            )
        """)



def record_execution_error(test_id: str, message: str):
    """Persist an orchestration error as a SIL test execution."""

    with psycopg.connect(DB, row_factory=dict_row) as conn:
        test = conn.execute("""
            SELECT requirement_id
            FROM test_cases
            WHERE id = %s
        """, (test_id,)).fetchone()

        row = conn.execute("""
            INSERT INTO test_executions (
                test_id,
                requirement_id,
                environment,
                verdict,
                duration_seconds,
                logs
            )
            VALUES (%s, %s, 'SIL', 'ERROR', 0, %s)
            RETURNING id
        """, (
            test_id,
            test["requirement_id"] if test else None,
            message[:20000]
        )).fetchone()

    return {
        "execution_id": row["id"],
        "test_id": test_id,
        "verdict": "ERROR",
        "duration_seconds": 0,
        "logs": message[:20000],
        "simulation": True
    }


def recover_interrupted_campaigns():
    """Mark campaigns left RUNNING by a previous backend process as interrupted."""

    with psycopg.connect(DB) as conn:
        result = conn.execute("""
            UPDATE test_campaigns
            SET status = 'INTERRUPTED',
                completed_at = now()
            WHERE status = 'RUNNING'
        """)

        return result.rowcount


@router.post("")
def create_campaign(request: CampaignRequest):
    if len(request.test_ids) != len(set(request.test_ids)):
        raise HTTPException(400, "Duplicate test IDs")

    unknown = [
        test_id for test_id in request.test_ids
        if test_id not in ALLOWED_TESTS
    ]

    if unknown:
        raise HTTPException(
            400,
            f"Tests not registered for SIL execution: {unknown}"
        )

    with psycopg.connect(DB, row_factory=dict_row) as conn:
        rows = conn.execute("""
            SELECT id, environment
            FROM test_cases
            WHERE id = ANY(%s)
        """, (request.test_ids,)).fetchall()

    available = {
        row["id"] for row in rows
        if row["environment"].upper() == "SIL"
    }

    if available != set(request.test_ids):
        raise HTTPException(
            400,
            "Some tests are missing or are not SIL tests"
        )

    with psycopg.connect(DB, row_factory=dict_row) as conn:
        campaign = conn.execute("""
            INSERT INTO test_campaigns(name, total_tests)
            VALUES (%s, %s)
            RETURNING id
        """, (request.name, len(request.test_ids))).fetchone()

    campaign_id = campaign["id"]
    results = []

    for test_id in request.test_ids:
        try:
            result = run_test(test_id)
        except Exception as exc:
            message = (
                "CAMPAIGN ORCHESTRATION ERROR\n"
                f"Exception type: {type(exc).__name__}\n"
                f"Message: {str(exc)}"
            )

            result = record_execution_error(
                test_id,
                message
            )

        results.append(result)

        if result["execution_id"] is not None:
            with psycopg.connect(DB) as conn:
                conn.execute("""
                    INSERT INTO campaign_executions(
                        campaign_id, execution_id
                    )
                    VALUES (%s, %s)
                """, (
                    campaign_id,
                    result["execution_id"]
                ))

    passed = sum(r["verdict"] == "PASSED" for r in results)
    failed = sum(r["verdict"] == "FAILED" for r in results)
    errors = len(results) - passed - failed

    status = "COMPLETED" if errors == 0 else "COMPLETED_WITH_ERRORS"

    with psycopg.connect(DB) as conn:
        conn.execute("""
            UPDATE test_campaigns
            SET status = %s,
                passed = %s,
                failed = %s,
                errors = %s,
                completed_at = now()
            WHERE id = %s
        """, (status, passed, failed, errors, campaign_id))

    return {
        "campaign_id": campaign_id,
        "name": request.name,
        "status": status,
        "total_tests": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "pass_rate": round(100 * passed / len(results), 1),
        "results": results
    }


@router.get("")
def list_campaigns():
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        return conn.execute("""
            SELECT *
            FROM test_campaigns
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()


@router.get("/{campaign_id}")
def get_campaign(campaign_id: int):
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        campaign = conn.execute("""
            SELECT *
            FROM test_campaigns
            WHERE id = %s
        """, (campaign_id,)).fetchone()

        if campaign is None:
            raise HTTPException(404, "Campaign not found")

        executions = conn.execute("""
            SELECT e.*
            FROM campaign_executions ce
            JOIN test_executions e
                ON e.id = ce.execution_id
            WHERE ce.campaign_id = %s
            ORDER BY e.id
        """, (campaign_id,)).fetchall()

    return {
        **campaign,
        "executions": executions
    }
