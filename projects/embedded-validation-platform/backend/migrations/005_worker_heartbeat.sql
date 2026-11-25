BEGIN;
CREATE TABLE IF NOT EXISTS worker_heartbeats (
 worker_id TEXT PRIMARY KEY,
 environment TEXT NOT NULL,
 last_seen TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMIT;
