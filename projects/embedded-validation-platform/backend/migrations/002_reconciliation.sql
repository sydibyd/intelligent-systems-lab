BEGIN;

CREATE TABLE IF NOT EXISTS reconciliation_events (
    id BIGSERIAL PRIMARY KEY,

    ci_build_id BIGINT NOT NULL
        REFERENCES ci_builds(id),

    previous_status TEXT NOT NULL,
    observed_status TEXT,
    target_status TEXT,

    action TEXT NOT NULL CHECK (
        action IN (
            'FINALIZE',
            'KEEP_RUNNING',
            'DEFER',
            'NO_CHANGE',
            'CONFLICT'
        )
    ),

    reason TEXT NOT NULL,

    applied BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reconciliation_build
    ON reconciliation_events(ci_build_id, created_at);

CREATE INDEX IF NOT EXISTS idx_ci_builds_running_age
    ON ci_builds(created_at, id)
    WHERE status = 'RUNNING';

COMMIT;
