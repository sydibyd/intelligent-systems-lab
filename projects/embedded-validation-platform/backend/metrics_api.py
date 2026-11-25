import os
import psycopg
from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()

METRICS = (
    ("evap_execution_jobs", "execution_jobs", "status",
     ("QUEUED","RUNNING","COMPLETED","ERROR","INTERRUPTED","CANCELLED")),
    ("evap_test_executions", "test_executions", "verdict",
     ("PASSED","FAILED","ERROR")),
    ("evap_ai_drafts", "ai_test_drafts", "status",
     ("PENDING_REVIEW","APPROVED","REJECTED")),
    ("evap_reconciliation_events", "reconciliation_events", "action",
     ("FINALIZE","KEEP_RUNNING","DEFER","NO_CHANGE","CONFLICT")),
)


@router.get("/api/metrics", response_class=PlainTextResponse)
def metrics():
    lines = []
    with psycopg.connect(os.environ["DATABASE_URL"], connect_timeout=5,
                         options="-c statement_timeout=5000") as conn:
        for name, table, label, values in METRICS:
            counts = dict(conn.execute(
                f"SELECT {label}, count(*) FROM {table} GROUP BY {label}"
            ).fetchall())
            lines.extend([f"# HELP {name} Current persisted records by {label}.",
                          f"# TYPE {name} gauge"])
            for value in values:
                lines.append(f'{name}{{{label}="{value}"}} {counts.get(value, 0)}')
        expired = conn.execute("""
            SELECT count(*) FROM execution_jobs
            WHERE status='RUNNING' AND lease_until<=now()
        """).fetchone()[0]
        lines.extend(["# TYPE evap_expired_job_leases gauge",
                      f"evap_expired_job_leases {expired}"])
        active = conn.execute("""
            SELECT count(*) FROM worker_heartbeats
            WHERE last_seen > now()-interval '60 seconds'
        """).fetchone()[0]
        lines.extend(["# TYPE evap_active_workers gauge",
                      f"evap_active_workers {active}"])
    return PlainTextResponse("\n".join(lines)+"\n",
                             media_type="text/plain; version=0.0.4")
