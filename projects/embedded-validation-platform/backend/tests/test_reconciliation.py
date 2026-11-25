import pytest

from reconciliation import (
    Action,
    TERMINAL_STATUSES,
    evaluate_build,
)


@pytest.mark.parametrize(
    "status", sorted(TERMINAL_STATUSES)
)
def test_recover_terminal_build(status):
    decision = evaluate_build(
        "RUNNING", True, False, status, False
    )
    assert decision.action == Action.FINALIZE
    assert decision.target_status == status


def test_jenkins_unavailable():
    decision = evaluate_build(
        "RUNNING", False, None, None, False
    )
    assert decision.action == Action.DEFER


def test_build_still_running():
    decision = evaluate_build(
        "RUNNING", True, True, None, False
    )
    assert decision.action == Action.KEEP_RUNNING


def test_active_campaign():
    decision = evaluate_build(
        "RUNNING", True, False, "SUCCESS", True
    )
    assert decision.action == Action.DEFER
    assert decision.reason == "ACTIVE_CAMPAIGN"


def test_idempotent_finalization():
    decision = evaluate_build(
        "SUCCESS", True, False, "SUCCESS", False
    )
    assert decision.action == Action.NO_CHANGE


def test_terminal_status_conflict():
    decision = evaluate_build(
        "SUCCESS", True, False, "FAILURE", False
    )
    assert decision.action == Action.CONFLICT


@pytest.mark.parametrize(
    "result", [None, "UNKNOWN", "RUNNING", ""]
)
def test_invalid_jenkins_result(result):
    decision = evaluate_build(
        "RUNNING", True, False, result, False
    )
    assert decision.action == Action.DEFER


def test_unknown_jenkins_state():
    decision = evaluate_build(
        "RUNNING", True, None, "SUCCESS", False
    )
    assert decision.action == Action.DEFER


def test_invalid_database_status():
    decision = evaluate_build(
        "UNKNOWN", True, False, "SUCCESS", False
    )
    assert decision.action == Action.DEFER


def test_database_finalized_jenkins_running():
    decision = evaluate_build(
        "SUCCESS", True, True, None, False
    )
    assert decision.action == Action.CONFLICT
