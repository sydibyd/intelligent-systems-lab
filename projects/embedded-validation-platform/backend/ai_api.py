import os
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Literal
from ai_generator import generate

router = APIRouter(prefix="/api/ai-drafts")


def connect():
    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row, connect_timeout=5)


def actor(request):
    identity = getattr(request.state, "identity", None)
    if identity is None:
        raise HTTPException(403, "Authenticated identity required for AI operations")
    return identity.name


class GenerateRequest(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=100)


class ReviewRequest(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str = Field(min_length=10, max_length=2000)


@router.post("", status_code=201)
def create_draft(payload: GenerateRequest, request: Request):
    name = actor(request)
    if os.getenv("EVAP_AI_ENABLED") != "true":
        raise HTTPException(503, "External AI generation disabled")
    with connect() as conn:
        row = conn.execute("SELECT description FROM requirements WHERE id=%s",
                           (payload.requirement_id,)).fetchone()
    if not row or not row["description"]:
        raise HTTPException(404, "Requirement description not found")
    try:
        proposal = generate(payload.requirement_id, row["description"])
    except Exception:
        raise HTTPException(502, "AI generation failed") from None
    with connect() as conn:
        return conn.execute("""
            INSERT INTO ai_test_drafts(requirement_id,requirement_snapshot,proposal,requested_by)
            VALUES (%s,%s,%s,%s) RETURNING *
        """, (payload.requirement_id,row["description"],Jsonb(proposal),name)).fetchone()


@router.get("")
def list_drafts():
    with connect() as conn:
        return conn.execute("SELECT * FROM ai_test_drafts ORDER BY id DESC LIMIT 100").fetchall()


@router.patch("/{draft_id}")
def review(draft_id: int, payload: ReviewRequest, request: Request):
    name = actor(request)
    if not payload.reason.strip():
        raise HTTPException(400, "Review reason required")
    with connect() as conn:
        row = conn.execute("SELECT * FROM ai_test_drafts WHERE id=%s FOR UPDATE",
                           (draft_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Draft not found")
        if row["status"] != "PENDING_REVIEW" or row["requested_by"] == name:
            raise HTTPException(409, "Independent pending review required")
        if payload.decision == "APPROVED":
            if not row["proposal"]["evaluation"]["structurally_valid"]:
                raise HTTPException(409, "Invalid draft cannot be approved")
            req = conn.execute("SELECT description FROM requirements WHERE id=%s",
                               (row["requirement_id"],)).fetchone()
            if not req or req["description"] != row["requirement_snapshot"]:
                raise HTTPException(409, "Requirement changed; regenerate draft")
        return conn.execute("""
            UPDATE ai_test_drafts SET status=%s,reviewed_by=%s,review_reason=%s,
            reviewed_at=now() WHERE id=%s RETURNING *
        """, (payload.decision,name,payload.reason,draft_id)).fetchone()
