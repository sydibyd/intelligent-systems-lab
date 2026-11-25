import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from execution_api import ALLOWED_TESTS
from execution_queue import ExecutionQueue

router = APIRouter(prefix="/api/jobs", tags=["Async execution"])
queue = ExecutionQueue(os.environ["DATABASE_URL"])


class JobRequest(BaseModel):
    test_id: str = Field(min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=16, max_length=128)


def public_job(row):
    return {k: v for k, v in row.items() if k not in {"lease_token", "idempotency_key"}}


@router.post("", status_code=202)
def submit(payload: JobRequest, request: Request):
    if payload.test_id not in ALLOWED_TESTS:
        raise HTTPException(400, "Only registered SIL tests are enabled")
    actor = getattr(request.state, "identity", None)
    with queue.connect() as conn:
        test = conn.execute("SELECT environment FROM test_cases WHERE id=%s",
                            (payload.test_id,)).fetchone()
    if not test or (test["environment"] or "").upper() != "SIL":
        raise HTTPException(400, "Registered SIL test required")
    try:
        return public_job(queue.enqueue(payload.test_id, "SIL",
                                actor.name if actor else "development",
                                payload.idempotency_key))
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("")
def list_jobs():
    with queue.connect() as conn:
        return [public_job(row) for row in conn.execute(
            "SELECT * FROM execution_jobs ORDER BY id DESC LIMIT 100").fetchall()]


@router.get("/{job_id}")
def get_job(job_id: int):
    with queue.connect() as conn:
        row = conn.execute("SELECT * FROM execution_jobs WHERE id=%s", (job_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Job not found")
    return public_job(row)
