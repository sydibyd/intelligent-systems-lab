import pytest
from security import allowed


@pytest.mark.parametrize("role", ["admin", "architect", "engineer"])
def test_generation_allowed(role):
    assert allowed(role, "POST", "/api/ai-drafts")


@pytest.mark.parametrize("role", ["viewer", "ci"])
def test_generation_denied(role):
    assert not allowed(role, "POST", "/api/ai-drafts")


@pytest.mark.parametrize("role", ["admin", "architect"])
def test_review_allowed(role):
    assert allowed(role, "PATCH", "/api/ai-drafts/1")


@pytest.mark.parametrize("role", ["engineer", "viewer", "ci"])
def test_review_denied(role):
    assert not allowed(role, "PATCH", "/api/ai-drafts/1")


def test_ci_cannot_read_ai_drafts():
    assert not allowed("ci", "GET", "/api/ai-drafts")
    assert not allowed("ci", "HEAD", "/api/ai-drafts")
