import os
from datetime import datetime, timezone
from unittest.mock import MagicMock

import psycopg
import pytest

from jenkins_client import JenkinsState
from reconciliation_service import ReconciliationService


DB = os.getenv("EVAP_INTEGRATION_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DB,
    reason="Integration database not configured",
)

SHA = "a" * 40
INSTANCE = "integration-test"
PIPELINE = "EVAP-INTEGRATION"


@pytest.fixture
def context():
    from urllib.parse import urlsplit

    parsed = urlsplit(DB)

    assert parsed.hostname == "evap-migration-test-db"
    assert parsed.path == "/evap_reconciliation_ci"
    assert not parsed.query

    created_at = datetime.now(timezone.utc)
    timestamp = int(created_at.timestamp() * 1000)

    url = "http://jenkins/job/EVAP-INTEGRATION/1/"

    with psycopg.connect(DB) as conn:
        build_id = conn.execute("""
            INSERT INTO ci_builds (
                ci_instance,
                pipeline_name,
                build_number,
                build_url,
                git_commit,
                git_branch,
                trigger_source,
                validation_scenario,
                status,
                created_at
            )
            VALUES (
                %s, %s, 1, %s, %s,
                'integration-test',
                'MANUAL',
                'NORMAL',
                'RUNNING',
                %s
            )
            RETURNING id
        """, (
            INSTANCE,
            PIPELINE,
            url,
            SHA,
            created_at,
        )).fetchone()[0]

    metadata = {
        "number": 1,
        "building": False,
        "result": "FAILURE",
        "timestamp": timestamp,
        "duration": 10000,
        "url": url,
        "actions": [
            {"lastBuiltRevision": {"SHA1": SHA}}
        ],
    }

    client = MagicMock()

    client.get_build.return_value = JenkinsState(
        reachable=True,
        building=False,
        result="FAILURE",
        metadata=metadata,
    )

    service = ReconciliationService(
        DB,
        {(INSTANCE, PIPELINE): client},
    )

    try:
        yield service, build_id, client, metadata
    finally:
        with psycopg.connect(DB) as conn:
            conn.execute(
                "DELETE FROM reconciliation_events "
                "WHERE ci_build_id = %s",
                (build_id,),
            )
            conn.execute(
                "DELETE FROM ci_builds WHERE id = %s",
                (build_id,),
            )


def snapshot(build_id):
    with psycopg.connect(DB) as conn:
        status = conn.execute(
            "SELECT status FROM ci_builds WHERE id = %s",
            (build_id,),
        ).fetchone()[0]

        events = conn.execute(
            "SELECT COUNT(*) FROM reconciliation_events "
            "WHERE ci_build_id = %s",
            (build_id,),
        ).fetchone()[0]

    return status, events


def test_dry_run_no_writes(context):
    service, build_id, _, _ = context

    result = service.reconcile_build(
        build_id, dry_run=True
    )

    assert result["action"] == "FINALIZE"
    assert not result["applied"]
    assert snapshot(build_id) == ("RUNNING", 0)


def test_transactional_recovery(context):
    service, build_id, _, _ = context

    result = service.reconcile_build(
        build_id, dry_run=False
    )

    assert result["applied"]
    assert snapshot(build_id) == ("FAILURE", 1)


def test_idempotent_recovery(context):
    service, build_id, _, _ = context

    service.reconcile_build(build_id, dry_run=False)

    result = service.reconcile_build(
        build_id, dry_run=False
    )

    assert result["action"] == "NO_CHANGE"
    assert not result["applied"]
    assert snapshot(build_id) == ("FAILURE", 2)


def test_missing_git_metadata(context):
    service, build_id, client, metadata = context

    metadata["actions"] = []

    result = service.reconcile_build(
        build_id, dry_run=False
    )

    assert result["action"] == "DEFER"
    assert result["reason"] == "GIT_METADATA_MISSING"
    assert not result["applied"]
    assert snapshot(build_id) == ("RUNNING", 1)


def test_jenkins_unavailable(context):
    service, build_id, client, _ = context

    client.get_build.return_value = JenkinsState(
        False,
        reason="JENKINS_QUERY_FAILED",
    )

    result = service.reconcile_build(
        build_id, dry_run=False
    )

    assert result["action"] == "DEFER"
    assert snapshot(build_id) == ("RUNNING", 1)


def test_terminal_conflict(context):
    service, build_id, client, metadata = context

    service.reconcile_build(build_id, dry_run=False)

    metadata["result"] = "SUCCESS"

    client.get_build.return_value = JenkinsState(
        True,
        building=False,
        result="SUCCESS",
        metadata=metadata,
    )

    result = service.reconcile_build(
        build_id, dry_run=False
    )

    assert result["action"] == "CONFLICT"
    assert not result["applied"]
    assert snapshot(build_id) == ("FAILURE", 2)
