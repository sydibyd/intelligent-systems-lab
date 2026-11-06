import os
import sys
import time
import subprocess
from contextlib import contextmanager

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api")

DB = os.environ["DATABASE_URL"]

SIL_ROOT = "/opt/evap/sil"

ALLOWED_TESTS = {
    "TC-004": "tests/test_can_timeout.py::test_sw_004_can_timeout",
    "TC-008": "tests/test_startup.py::test_sw_008_startup_initialization",
    "TC-009": "tests/test_can_transmission.py::test_sw_009_can_transmission",
    "TC-011": "tests/test_soc.py::test_sw_011_soc_calculation"
}


@contextmanager
def connection():
    with psycopg.connect(DB, row_factory=dict_row) as conn:
        yield conn


def initialize_execution_database():
    with connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_executions (
                id BIGSERIAL PRIMARY KEY,
                test_id TEXT NOT NULL,
                requirement_id TEXT,
                environment TEXT NOT NULL,
                verdict TEXT NOT NULL,
                duration_seconds DOUBLE PRECISION,
                logs TEXT,
                executed_at TIMESTAMPTZ DEFAULT now()
            )
        """)


@router.get("/executions")
def list_executions():
    with connection() as conn:
        return conn.execute("""
            SELECT *
            FROM test_executions
            ORDER BY id DESC
            LIMIT 100
        """).fetchall()


@router.get("/executions/{execution_id}")
def get_execution(execution_id: int):
    with connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM test_executions
            WHERE id = %s
        """, (execution_id,)).fetchone()

    if not row:
        raise HTTPException(404, "Execution not found")

    return row


@router.post("/executions/{test_id}")
def run_test(test_id: str):

    if test_id not in ALLOWED_TESTS:
        raise HTTPException(
            400,
            "Test is not registered for SIL execution"
        )

    with connection() as conn:
        test = conn.execute("""
            SELECT id, requirement_id, environment
            FROM test_cases
            WHERE id = %s
        """, (test_id,)).fetchone()

    if not test:
        raise HTTPException(404, "Test case not found")

    if test["environment"].upper() != "SIL":
        raise HTTPException(
            400,
            "Only SIL tests can run in this version"
        )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        ALLOWED_TESTS[test_id]
    ]

    start = time.monotonic()

    try:
        result = subprocess.run(
            command,
            cwd=SIL_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"
            }
        )

        if result.returncode == 0:
            verdict = "PASSED"
        elif result.returncode == 1:
            verdict = "FAILED"
        else:
            verdict = "ERROR"

        logs = result.stdout + "\n" + result.stderr

    except subprocess.TimeoutExpired:
        verdict = "ERROR"
        logs = "Test execution timed out after 30 seconds"

    except Exception as exc:
        verdict = "ERROR"
        logs = f"Runner error: {type(exc).__name__}"

    duration = round(time.monotonic() - start, 3)

    with connection() as conn:
        row = conn.execute("""
            INSERT INTO test_executions
            (
                test_id,
                requirement_id,
                environment,
                verdict,
                duration_seconds,
                logs
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            test_id,
            test["requirement_id"],
            "SIL",
            verdict,
            duration,
            logs[:20000]
        )).fetchone()

    return {
        "execution_id": row["id"],
        "test_id": test_id,
        "verdict": verdict,
        "duration_seconds": duration,
        "logs": logs[:20000],
        "simulation": True
    }
