"""Minimal RC2 manual test design. Scripts are stored, never executed by the API."""
import os
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

router = APIRouter(prefix="/api/design")

class Case(BaseModel):
    test_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    requirement_id: str = Field(min_length=1,max_length=120)
    name: str = Field(min_length=1,max_length=200)
    expected: str = Field(min_length=1,max_length=4000)

@router.post("/cases", status_code=201)
def create_case(case: Case):
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as c:
        if not c.execute("SELECT id FROM requirements WHERE id=%s FOR KEY SHARE",(case.requirement_id,)).fetchone():
            raise HTTPException(404,"Requirement not found")
        payload = {"Test_ID":case.test_id,"Requirement_ID":case.requirement_id,"Test_Name":case.name,"Environment":"SIL","Status":"Draft","Expected_Result":case.expected}
        row=c.execute("INSERT INTO test_cases(id,requirement_id,name,environment,status,payload) VALUES (%s,%s,%s,'SIL','Draft',%s) ON CONFLICT DO NOTHING RETURNING id",(case.test_id,case.requirement_id,case.name,Jsonb(payload))).fetchone()
        if not row:
            raise HTTPException(409,"Test ID already exists")
        return payload
