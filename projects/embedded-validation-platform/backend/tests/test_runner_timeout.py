import subprocess
from unittest.mock import patch

from execution_api import run_test


class FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append((query, params))
        return FakeCursor(self.rows.pop(0))

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_runner_timeout_is_persisted():
    db = FakeConnection([
        {
            "id": "TC-004",
            "requirement_id": "SW-004",
            "environment": "SIL",
        },
        {"id": 999},
    ])

    timeout = subprocess.TimeoutExpired(
        cmd=["pytest"],
        timeout=30,
        output=b"partial stdout",
        stderr=b"partial stderr",
    )

    with (
        patch("execution_api.connection", return_value=db),
        patch("execution_api.subprocess.run", side_effect=timeout),
    ):
        result = run_test("TC-004")

    assert result["verdict"] == "ERROR"
    assert result["execution_id"] == 999
    assert result["test_id"] == "TC-004"
    assert result["duration_seconds"] >= 0

    assert "EXECUTION TIMEOUT" in result["logs"]
    assert "partial stdout" in result["logs"]
    assert "partial stderr" in result["logs"]

    inserts = [
        params
        for query, params in db.queries
        if "INSERT INTO test_executions" in query
    ]

    assert len(inserts) == 1
    assert inserts[0][0] == "TC-004"
    assert inserts[0][3] == "ERROR"
