import os
from typing import Literal

import psycopg
from psycopg.rows import dict_row
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field


DB = os.environ["DATABASE_URL"]

router = APIRouter(
    prefix="/api/ci-builds",
    tags=["CI/CD Traceability"]
)


FinalStatus = Literal[
    "SUCCESS",
    "FAILURE",
    "ABORTED",
    "UNSTABLE",
    "INTERRUPTED",
    "NOT_BUILT"
]


class BuildRegistration(BaseModel):
    ci_instance: str = Field(min_length=1, max_length=200)
    pipeline_name: str = Field(min_length=1, max_length=200)
    build_number: int = Field(gt=0, le=9223372036854775807)
    build_url: str | None = Field(default=None, max_length=2048)

    git_commit: str = Field(
        pattern=r"^[0-9a-f]{40}$"
    )

    git_branch: str = Field(min_length=1, max_length=250)

    trigger_source: str = Field(
        default="UNKNOWN",
        max_length=100
    )

    validation_scenario: str = Field(
        default="NORMAL",
        max_length=100
    )


class BuildFinalization(BaseModel):
    status: FinalStatus


def get_build_or_404(conn, build_id):
    build = conn.execute("""
        SELECT *
        FROM ci_builds
        WHERE id = %s
    """, (build_id,)).fetchone()

    if build is None:
        raise HTTPException(404, "CI build not found")

    return build


@router.post("", status_code=201)
def register_build(request: BuildRegistration):

    with psycopg.connect(DB, row_factory=dict_row) as conn:

        build = conn.execute("""
            INSERT INTO ci_builds (
                ci_instance,
                pipeline_name,
                build_number,
                build_url,
                git_commit,
                git_branch,
                trigger_source,
                validation_scenario
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (
                ci_instance,
                pipeline_name,
                build_number
            )
            DO NOTHING
            RETURNING *
        """, (
            request.ci_instance,
            request.pipeline_name,
            request.build_number,
            request.build_url,
            request.git_commit,
            request.git_branch,
            request.trigger_source,
            request.validation_scenario
        )).fetchone()

        if build is not None:
            return build

        existing = conn.execute("""
            SELECT *
            FROM ci_builds
            WHERE ci_instance = %s
              AND pipeline_name = %s
              AND build_number = %s
        """, (
            request.ci_instance,
            request.pipeline_name,
            request.build_number
        )).fetchone()

        if existing is None:
            raise HTTPException(
                409,
                "Build registration conflict"
            )

        for field, value in request.model_dump().items():
            if existing[field] != value:
                raise HTTPException(
                    409,
                    "Build identity metadata conflict"
                )

        return existing


@router.get("")
def list_builds(
    git_commit: str | None = Query(
        default=None,
        pattern=r"^[0-9a-f]{40}$"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0)
):
    with psycopg.connect(DB, row_factory=dict_row) as conn:

        if git_commit is not None:
            return conn.execute("""
                SELECT *
                FROM ci_builds
                WHERE git_commit = %s
                ORDER BY id DESC
                LIMIT %s OFFSET %s
            """, (
                git_commit,
                limit,
                offset
            )).fetchall()

        return conn.execute("""
            SELECT *
            FROM ci_builds
            ORDER BY id DESC
            LIMIT %s OFFSET %s
        """, (limit, offset)).fetchall()


@router.get("/{build_id}")
def get_build(build_id: int):

    with psycopg.connect(DB, row_factory=dict_row) as conn:
        return get_build_or_404(conn, build_id)


@router.patch("/{build_id}")
def finalize_build(
    build_id: int,
    request: BuildFinalization
):
    with psycopg.connect(DB, row_factory=dict_row) as conn:

        build = conn.execute("""
            SELECT *
            FROM ci_builds
            WHERE id = %s
            FOR UPDATE
        """, (build_id,)).fetchone()

        if build is None:
            raise HTTPException(404, "CI build not found")

        if build["status"] == request.status:
            return build

        if build["status"] != "RUNNING":
            raise HTTPException(
                409,
                "CI build is already finalized"
            )

        active_campaign = conn.execute("""
            SELECT id
            FROM test_campaigns
            WHERE ci_build_id = %s
              AND status = 'RUNNING'
            LIMIT 1
        """, (build_id,)).fetchone()

        if active_campaign is not None:
            raise HTTPException(
                409,
                "CI build has an active campaign"
            )

        return conn.execute("""
            UPDATE ci_builds
            SET status = %s,
                completed_at = now()
            WHERE id = %s
            RETURNING *
        """, (
            request.status,
            build_id
        )).fetchone()


@router.get("/{build_id}/campaigns")
def get_build_campaigns(build_id: int):

    with psycopg.connect(DB, row_factory=dict_row) as conn:

        get_build_or_404(conn, build_id)

        return conn.execute("""
            SELECT *
            FROM test_campaigns
            WHERE ci_build_id = %s
            ORDER BY id
        """, (build_id,)).fetchall()


@router.get("/{build_id}/executions")
def get_build_executions(build_id: int):

    with psycopg.connect(DB, row_factory=dict_row) as conn:

        get_build_or_404(conn, build_id)

        return conn.execute("""
            SELECT
                e.*,
                c.id AS campaign_id
            FROM test_campaigns c
            JOIN campaign_executions ce
                ON ce.campaign_id = c.id
            JOIN test_executions e
                ON e.id = ce.execution_id
            WHERE c.ci_build_id = %s
            ORDER BY c.id, e.id
        """, (build_id,)).fetchall()
