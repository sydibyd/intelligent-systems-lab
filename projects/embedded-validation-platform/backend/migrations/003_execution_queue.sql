BEGIN;
CREATE TABLE IF NOT EXISTS execution_jobs (
    id BIGSERIAL PRIMARY KEY,
    test_id TEXT NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('SIL','HIL')),
    status TEXT NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED','RUNNING','COMPLETED','ERROR','INTERRUPTED','CANCELLED')),
    requested_by TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    worker_id TEXT,
    lease_token UUID,
    lease_until TIMESTAMPTZ,
    execution_id BIGINT REFERENCES test_executions(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(requested_by,idempotency_key)
);
CREATE INDEX IF NOT EXISTS execution_jobs_pending_idx
    ON execution_jobs(environment,id) WHERE status='QUEUED';
CREATE INDEX IF NOT EXISTS execution_jobs_lease_idx
    ON execution_jobs(lease_until) WHERE status='RUNNING';
COMMIT;
