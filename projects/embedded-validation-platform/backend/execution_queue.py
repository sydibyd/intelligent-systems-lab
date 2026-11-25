import uuid
import psycopg
from psycopg.rows import dict_row


class ExecutionQueue:
    def __init__(self, database_url):
        self.database_url = database_url

    def connect(self):
        return psycopg.connect(self.database_url, row_factory=dict_row,
                               connect_timeout=5, options="-c statement_timeout=10000")

    def enqueue(self, test_id, environment, actor, key):
        with self.connect() as conn:
            row = conn.execute("""
                INSERT INTO execution_jobs(test_id,environment,requested_by,idempotency_key)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT(requested_by,idempotency_key) DO NOTHING RETURNING *
            """, (test_id, environment, actor, key)).fetchone()
            if row is None:
                row = conn.execute("""
                    SELECT * FROM execution_jobs WHERE requested_by=%s AND idempotency_key=%s
                """, (actor,key)).fetchone()
                if (row["test_id"],row["environment"]) != (test_id,environment):
                    raise ValueError("Idempotency key conflict")
            return row

    def claim(self, worker_id, environment, lease_seconds=120):
        if environment not in {"SIL","HIL"} or not 60 <= lease_seconds <= 3600:
            raise ValueError("Invalid worker configuration")
        with self.connect() as conn:
            return conn.execute("""
                WITH candidate AS (
                    SELECT id FROM execution_jobs WHERE status='QUEUED' AND environment=%s
                    ORDER BY id FOR UPDATE SKIP LOCKED LIMIT 1
                )
                UPDATE execution_jobs j SET status='RUNNING', worker_id=%s,
                    lease_token=%s, lease_until=now()+(%s*interval '1 second'), started_at=now()
                FROM candidate WHERE j.id=candidate.id RETURNING j.*
            """, (environment,worker_id,uuid.uuid4(),lease_seconds)).fetchone()

    def finish(self, job_id, token, verdict, duration, logs):
        if verdict not in {"PASSED","FAILED","ERROR"} or not 0 <= duration <= 3600:
            raise ValueError("Invalid result")
        with self.connect() as conn:
            job = conn.execute("""
                SELECT * FROM execution_jobs WHERE id=%s AND lease_token=%s
                AND status='RUNNING' AND lease_until>now() FOR UPDATE
            """, (job_id,token)).fetchone()
            if job is None:
                return False
            result = conn.execute("""
                INSERT INTO test_executions(test_id,requirement_id,environment,verdict,duration_seconds,logs)
                VALUES (%s,(SELECT requirement_id FROM test_cases WHERE id=%s),%s,%s,%s,%s)
                RETURNING id
            """, (job["test_id"],job["test_id"],job["environment"],verdict,duration,logs[:20000])).fetchone()
            conn.execute("""
                UPDATE execution_jobs SET status=%s,execution_id=%s,completed_at=now(),
                    lease_token=NULL,lease_until=NULL WHERE id=%s
            """, ("ERROR" if verdict=="ERROR" else "COMPLETED",result["id"],job_id))
            return True

    def expire(self):
        # Never automatically replay potentially side-effecting hardware tests.
        with self.connect() as conn:
            return conn.execute("""
                UPDATE execution_jobs SET status='INTERRUPTED',completed_at=now(),
                    lease_token=NULL,lease_until=NULL
                WHERE status='RUNNING' AND lease_until<=now()
            """).rowcount
