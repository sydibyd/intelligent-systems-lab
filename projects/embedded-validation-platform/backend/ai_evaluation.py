"""Provider-independent test draft contract. Drafts are never executable."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class TestStep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1, max_length=1000)
    expected: str = Field(min_length=1, max_length=1000)


class TestDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requirement_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    environment: Literal["SIL", "HIL"]
    category: Literal["nominal", "boundary", "negative", "fault"]
    preconditions: list[str] = Field(min_length=1, max_length=20)
    steps: list[TestStep] = Field(min_length=1, max_length=20)


def evaluate(draft: TestDraft, requirement_id: str):
    issues = []
    if draft.requirement_id != requirement_id:
        issues.append("REQUIREMENT_MISMATCH")
    if not draft.title.strip():
        issues.append("EMPTY_TITLE")
    if any(not p.strip() for p in draft.preconditions):
        issues.append("EMPTY_PRECONDITION")
    if any(not s.action.strip() or not s.expected.strip() for s in draft.steps):
        issues.append("INCOMPLETE_STEP")
    if len({s.action.strip().casefold() for s in draft.steps}) != len(draft.steps):
        issues.append("DUPLICATE_ACTION")
    return {"structurally_valid": not issues, "issues": issues,
            "human_review_required": True, "executable": False}
