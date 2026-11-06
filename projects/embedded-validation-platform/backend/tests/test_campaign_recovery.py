from unittest.mock import patch

from campaign_api import recover_interrupted_campaigns


class FakeCursor:
    rowcount = 2


class FakeConnection:
    def __init__(self):
        self.queries = []

    def execute(self, query, params=None):
        self.queries.append(query)
        return FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_recover_interrupted_campaigns():
    db = FakeConnection()

    with patch("campaign_api.psycopg.connect", return_value=db):
        recovered = recover_interrupted_campaigns()

    assert recovered == 2
    assert len(db.queries) == 1

    query = db.queries[0]

    assert "UPDATE test_campaigns" in query
    assert "status = 'INTERRUPTED'" in query
    assert "WHERE status = 'RUNNING'" in query
    assert "completed_at = now()" in query
