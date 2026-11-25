import psycopg
from psycopg.rows import dict_row

from jenkins_client import JenkinsState
from reconciliation import Action, evaluate_build


class ReconciliationService:

    def __init__(self, database_url, trusted_clients):
        self.database_url = database_url
        self.trusted_clients = trusted_clients

    def reconcile_build(self, build_id, dry_run=True):

        with psycopg.connect(
            self.database_url,
            row_factory=dict_row,
        ) as conn:

            build = conn.execute("""
                SELECT *
                FROM ci_builds
                WHERE id = %s
            """, (build_id,)).fetchone()

        if build is None:
            raise ValueError("CI build not found")

        identity = (
            build["ci_instance"],
            build["pipeline_name"],
        )

        client = self.trusted_clients.get(identity)

        if client is None:
            state = JenkinsState(
                False,
                reason="UNTRUSTED_JENKINS_JOB",
            )
        else:
            state = client.get_build(
                build["pipeline_name"],
                build["build_number"],
            )

        with psycopg.connect(
            self.database_url,
            row_factory=dict_row,
        ) as conn:

            current = conn.execute("""
                SELECT *
                FROM ci_builds
                WHERE id = %s
                FOR UPDATE
            """, (build_id,)).fetchone()

            if current is None:
                raise ValueError("CI build disappeared")

            for field in (
                "ci_instance",
                "pipeline_name",
                "build_number",
                "git_commit",
            ):
                if current[field] != build[field]:
                    raise RuntimeError(
                        "Build identity changed"
                    )

            active = conn.execute("""
                SELECT EXISTS (
                    SELECT 1
                    FROM test_campaigns
                    WHERE ci_build_id = %s
                      AND status = 'RUNNING'
                ) AS active
            """, (build_id,)).fetchone()["active"]

            decision = evaluate_build(
                current["status"],
                state.reachable,
                state.building,
                state.result,
                active,
            )

            applied = False

            if (
                decision.action == Action.FINALIZE
                and not dry_run
            ):
                conn.execute("""
                    UPDATE ci_builds
                    SET status = %s,
                        completed_at = now()
                    WHERE id = %s
                      AND status = 'RUNNING'
                """, (
                    decision.target_status,
                    build_id,
                ))

                applied = True

            reason = decision.reason

            if not state.reachable and state.reason:
                reason = state.reason

            if not dry_run:
                conn.execute("""
                    INSERT INTO reconciliation_events (
                        ci_build_id,
                        previous_status,
                        observed_status,
                        target_status,
                        action,
                        reason,
                        applied
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    build_id,
                    current["status"],
                    state.result,
                    decision.target_status,
                    decision.action.value,
                    reason,
                    applied,
                ))

            return {
                "build_id": build_id,
                "previous_status": current["status"],
                "jenkins_result": state.result,
                "action": decision.action.value,
                "reason": reason,
                "target_status": decision.target_status,
                "applied": applied,
                "dry_run": dry_run,
            }

    def reconcile_pending(
        self,
        min_age_seconds=300,
        limit=100,
        dry_run=True,
    ):

        if not 60 <= min_age_seconds <= 86400:
            raise ValueError("Invalid minimum age")

        if not 1 <= limit <= 500:
            raise ValueError("Invalid batch limit")

        with psycopg.connect(
            self.database_url,
            row_factory=dict_row,
        ) as conn:

            builds = conn.execute("""
                SELECT id
                FROM ci_builds
                WHERE status = 'RUNNING'
                  AND created_at <= now()
                    - (%s * interval '1 second')
                ORDER BY created_at, id
                LIMIT %s
            """, (
                min_age_seconds,
                limit,
            )).fetchall()

        return [
            self.reconcile_build(
                build["id"],
                dry_run=dry_run,
            )
            for build in builds
        ]
