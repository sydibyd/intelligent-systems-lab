import pytest
from pydantic import ValidationError
from ai_evaluation import TestDraft, evaluate


def draft():
    return dict(requirement_id="REQ-1", title="Timeout validation",
                environment="SIL", category="fault", preconditions=["Initialized"],
                steps=[{"action":"Simulate timeout","expected":"Fault detected"}])


def test_valid_draft_is_not_executable():
    result = evaluate(TestDraft(**draft()), "REQ-1")
    assert result["structurally_valid"]
    assert result["human_review_required"]
    assert not result["executable"]


def test_traceability_mismatch():
    assert "REQUIREMENT_MISMATCH" in evaluate(TestDraft(**draft()), "REQ-2")["issues"]


def test_extra_code_rejected():
    with pytest.raises(ValidationError):
        TestDraft(**draft(), code="print(1)")


def test_blank_expected_result():
    data = draft()
    data["steps"][0]["expected"] = " "
    assert not evaluate(TestDraft(**data), "REQ-1")["structurally_valid"]
