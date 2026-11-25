from unittest.mock import MagicMock, patch

import pytest

from reconciliation_worker import RecoveryWorker


@pytest.fixture
def service():
    return MagicMock()


@pytest.mark.parametrize(
    "options",
    [
        {"interval_seconds": 0},
        {"interval_seconds": 3601},
        {"min_age_seconds": 0},
        {"batch_size": 0},
        {"batch_size": 501},
    ],
)
def test_invalid_configuration(service, options):
    with pytest.raises(ValueError):
        RecoveryWorker(service, **options)


def test_default_dry_run(service):
    worker = RecoveryWorker(service)
    assert worker.dry_run is True


def test_stop_signal(service):
    worker = RecoveryWorker(service)
    worker.stop()
    assert worker.stop_event.is_set()


def mock_database(locked=True, builds=None):
    conn = MagicMock()

    conn.execute.return_value.fetchone.return_value = (
        locked,
    )

    conn.execute.return_value.fetchall.return_value = (
        builds or []
    )

    return conn


@patch("reconciliation_worker.psycopg.connect")
def test_lock_contention(connect, service):

    conn = mock_database(locked=False)
    connect.return_value.__enter__.return_value = conn

    worker = RecoveryWorker(service)
    metrics = worker.run_cycle()

    assert metrics["skipped"]
    assert metrics["scanned"] == 0
    service.reconcile_build.assert_not_called()


@patch("reconciliation_worker.psycopg.connect")
def test_empty_cycle(connect, service):

    conn = mock_database()
    connect.return_value.__enter__.return_value = conn

    worker = RecoveryWorker(service)
    metrics = worker.run_cycle()

    assert metrics["scanned"] == 0
    assert metrics["finalized"] == 0


@patch("reconciliation_worker.psycopg.connect")
def test_successful_recovery(connect, service):

    conn = mock_database(builds=[(12,)])
    connect.return_value.__enter__.return_value = conn

    service.reconcile_build.return_value = {
        "action": "FINALIZE",
        "applied": True,
    }

    worker = RecoveryWorker(service, dry_run=False)
    metrics = worker.run_cycle()

    assert metrics["scanned"] == 1
    assert metrics["finalized"] == 1

    service.reconcile_build.assert_called_once_with(
        12,
        dry_run=False,
    )


@patch("reconciliation_worker.psycopg.connect")
def test_deferred_build(connect, service):

    conn = mock_database(builds=[(16,)])
    connect.return_value.__enter__.return_value = conn

    service.reconcile_build.return_value = {
        "action": "DEFER",
        "applied": False,
    }

    worker = RecoveryWorker(service)
    metrics = worker.run_cycle()

    assert metrics["deferred"] == 1
    assert metrics["finalized"] == 0
    assert worker.cursor == 16


@patch("reconciliation_worker.psycopg.connect")
def test_error_isolation(connect, service):

    conn = mock_database(builds=[(12,), (13,)])
    connect.return_value.__enter__.return_value = conn

    service.reconcile_build.side_effect = [
        RuntimeError("Synthetic failure"),
        {
            "action": "FINALIZE",
            "applied": False,
        },
    ]

    worker = RecoveryWorker(service)
    metrics = worker.run_cycle()

    assert metrics["scanned"] == 2
    assert metrics["errors"] == 1
    assert metrics["eligible"] == 1
    assert metrics["finalized"] == 0


@patch("reconciliation_worker.psycopg.connect")
def test_cursor_reset(connect, service):

    conn = mock_database()
    connect.return_value.__enter__.return_value = conn

    worker = RecoveryWorker(service)
    worker.cursor = 100

    worker.run_cycle()

    assert worker.cursor == 0
