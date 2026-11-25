import json
from unittest.mock import MagicMock, patch
import pytest
from ai_generator import generate


def test_disabled_by_default(monkeypatch):
    monkeypatch.delenv("EVAP_AI_ENABLED", raising=False)
    with pytest.raises(RuntimeError):
        generate("R1", "Requirement")


def test_mock_generation(monkeypatch):
    monkeypatch.setenv("EVAP_AI_ENABLED", "true")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-test-key")
    monkeypatch.setenv("EVAP_CLAUDE_MODEL", "test-model")
    draft = dict(requirement_id="R1", title="Test", environment="SIL",
                 category="nominal", preconditions=["Ready"],
                 steps=[dict(action="Stimulate", expected="Response")])
    response = MagicMock()
    response.__enter__.return_value.read.return_value = json.dumps({
        "stop_reason":"end_turn", "content":[{"type":"text","text":json.dumps(draft)}]
    }).encode()
    with patch("ai_generator.build_opener") as opener:
        opener.return_value.open.return_value = response
        result = generate("R1", "Requirement")
    assert result["status"] == "PENDING_REVIEW"
    assert result["evaluation"]["structurally_valid"]
    assert not result["evaluation"]["executable"]
