from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from campaign_api import CampaignRequest, create_campaign


def make_request(ci_build_id=None):
    return CampaignRequest(
        name="Campaign Association Test",
        test_ids=["TC-004"],
        ci_build_id=ci_build_id,
    )


def test_valid_ci_build_association():
    request = make_request(42)

    assert request.ci_build_id == 42


def test_manual_campaign_without_ci_build():
    request = make_request()

    assert request.ci_build_id is None


def test_reject_zero_ci_build_id():
    with pytest.raises(ValidationError):
        make_request(0)


def test_reject_negative_ci_build_id():
    with pytest.raises(ValidationError):
        make_request(-1)


def test_reject_unknown_ci_build():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [
        {"id": "TC-004", "environment": "SIL"}
    ]
    db.execute.return_value.fetchone.return_value = None

    with patch("campaign_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        with pytest.raises(HTTPException) as exc:
            create_campaign(make_request(42))

    assert exc.value.status_code == 404
    assert exc.value.detail == "CI build not found"


def test_reject_finalized_ci_build():
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [
        {"id": "TC-004", "environment": "SIL"}
    ]

    db.execute.return_value.fetchone.return_value = {
        "id": 42,
        "status": "SUCCESS",
    }

    with patch("campaign_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        with pytest.raises(HTTPException) as exc:
            create_campaign(make_request(42))

    assert exc.value.status_code == 409
    assert exc.value.detail == "CI build is already finalized"


def execute_mock_campaign(ci_build_id):
    db = MagicMock()
    db.execute.return_value.fetchall.return_value = [
        {"id": "TC-004", "environment": "SIL"}
    ]

    rows = []

    if ci_build_id is not None:
        rows.append({
            "id": ci_build_id,
            "status": "RUNNING",
        })

    rows.append({"id": 100})

    db.execute.return_value.fetchone.side_effect = rows

    execution = {
        "execution_id": 200,
        "test_id": "TC-004",
        "verdict": "PASSED",
        "duration_seconds": 0.25,
        "logs": "Unit test execution",
        "simulation": True,
    }

    with patch("campaign_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        with patch(
            "campaign_api.run_test",
            return_value=execution,
        ) as runner:

            result = create_campaign(
                make_request(ci_build_id)
            )

            runner.assert_called_once_with("TC-004")

    return result, db


def test_persist_ci_build_association():
    result, db = execute_mock_campaign(42)

    insert_calls = [
        call
        for call in db.execute.call_args_list
        if "INSERT INTO test_campaigns" in call.args[0]
    ]

    assert len(insert_calls) == 1

    parameters = insert_calls[0].args[1]

    assert parameters == (
        "Campaign Association Test",
        1,
        42,
    )

    assert result["campaign_id"] == 100
    assert result["status"] == "COMPLETED"


@pytest.mark.parametrize("ci_build_id", [42, None])
def test_return_ci_build_id(ci_build_id):
    result, db = execute_mock_campaign(ci_build_id)

    assert result["ci_build_id"] == ci_build_id
    assert result["passed"] == 1
    assert result["failed"] == 0
    assert result["errors"] == 0
    assert result["pass_rate"] == 100.0
