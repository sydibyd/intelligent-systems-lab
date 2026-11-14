BEGIN;

CREATE TABLE IF NOT EXISTS ci_builds (
    id BIGSERIAL PRIMARY KEY,

    ci_instance TEXT NOT NULL,
    pipeline_name TEXT NOT NULL,
    build_number BIGINT NOT NULL
        CHECK (build_number > 0),

    build_url TEXT,

    git_commit TEXT NOT NULL
        CHECK (git_commit ~ '^[0-9a-f]{40}$'),

    git_branch TEXT NOT NULL,

    trigger_source TEXT NOT NULL
        DEFAULT 'UNKNOWN',

    validation_scenario TEXT NOT NULL
        DEFAULT 'NORMAL',

    status TEXT NOT NULL DEFAULT 'RUNNING'
        CHECK (
            status IN (
                'RUNNING',
                'SUCCESS',
                'FAILURE',
                'ABORTED',
                'UNSTABLE',
                'INTERRUPTED',
                'NOT_BUILT'
            )
        ),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT ci_builds_unique_identity
        UNIQUE (
            ci_instance,
            pipeline_name,
            build_number
        )
);

ALTER TABLE test_campaigns
    ADD COLUMN IF NOT EXISTS ci_build_id BIGINT
        REFERENCES ci_builds(id);

ALTER TABLE test_campaigns
    ADD COLUMN IF NOT EXISTS backend_fingerprint TEXT;

ALTER TABLE test_campaigns
    ADD COLUMN IF NOT EXISTS sil_fingerprint TEXT;

CREATE INDEX IF NOT EXISTS idx_ci_builds_git_commit
    ON ci_builds(git_commit);

CREATE INDEX IF NOT EXISTS idx_ci_builds_status
    ON ci_builds(status);

CREATE INDEX IF NOT EXISTS idx_campaigns_ci_build_id
    ON test_campaigns(ci_build_id);

COMMIT;
