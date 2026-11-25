import os
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi import HTTPException
from ai_api import connect, create_draft, review, GenerateRequest, ReviewRequest


def test_ai_review(monkeypatch):
    if not os.getenv("EVAP_INTEGRATION_DATABASE_URL"):
        pytest.skip("Isolated integration database required")
    from urllib.parse import urlsplit
    url = os.environ["EVAP_INTEGRATION_DATABASE_URL"]
    parsed = urlsplit(url)
    assert parsed.hostname == "evap-migration-test-db"
    assert parsed.path == "/evap_reconciliation_ci"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("EVAP_AI_ENABLED", "true")
    rid = "AI-CI-REVIEW"
    def actor(name):
        return SimpleNamespace(state=SimpleNamespace(identity=SimpleNamespace(name=name)))
    with connect() as conn:
        conn.execute("INSERT INTO requirements(id,description,payload) VALUES (%s,%s,'{}')", (rid,"Synthetic requirement"))
    try:
        with patch("ai_api.generate", return_value={"evaluation":{"structurally_valid":True},"provider":"mock"}):
            draft = create_draft(GenerateRequest(requirement_id=rid), actor("engineer"))
        decision = ReviewRequest(decision="APPROVED",reason="Reviewed synthetic requirement")
        with pytest.raises(HTTPException) as error:
            review(draft["id"], decision, actor("engineer"))
        assert error.value.status_code == 409
        approved = review(draft["id"], decision, actor("architect"))
        assert approved["status"] == "APPROVED"
        assert approved["reviewed_by"] == "architect"
        with pytest.raises(HTTPException):
            review(draft["id"], decision, actor("other"))
    finally:
        with connect() as conn:
            conn.execute("DELETE FROM ai_test_drafts WHERE requirement_id=%s",(rid,))
            conn.execute("DELETE FROM requirements WHERE id=%s",(rid,))
