BEGIN;
CREATE TABLE IF NOT EXISTS ai_test_drafts (
 id BIGSERIAL PRIMARY KEY,
 requirement_id TEXT NOT NULL,
 requirement_snapshot TEXT NOT NULL,
 proposal JSONB NOT NULL,
 requested_by TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING_REVIEW' CHECK(status IN ('PENDING_REVIEW','APPROVED','REJECTED')),
 reviewed_by TEXT,
 review_reason TEXT,
 reviewed_at TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMIT;
