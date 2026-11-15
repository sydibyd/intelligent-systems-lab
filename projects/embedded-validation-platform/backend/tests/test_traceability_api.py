from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from traceability_api import (
    BuildRegistration,
    BuildFinalization,
    register_build,
    finalize_build,
    get_build_or_404,
)


def make_registration(**overrides):
    data = {
        "ci_instance": "jenkins-local",
        "pipeline_name": "EVAP-CI-CD",
        "build_number": 42,
        "git_commit": "a" * 40,
        "git_branch": "feature/test",
        "trigger_source": "SCM",
        "validation_scenario": "NORMAL",
    }

    data.update(overrides)

    return BuildRegistration(**data)


def test_valid_build_registration():
    request = make_registration()

    assert request.build_number == 42
    assert request.git_commit == "a" * 40


def test_invalid_git_commit():
    with pytest.raises(ValidationError):
        make_registration(git_commit="invalid")


def test_invalid_build_number():
    with pytest.raises(ValidationError):
        make_registration(build_number=0)


def test_invalid_final_status():
    with pytest.raises(ValidationError):
        BuildFinalization(status="RUNNING")


def test_register_new_build():
    request = make_registration()

    row = {
        **request.model_dump(),
        "id": 1,
        "status": "RUNNING",
    }

    db = MagicMock()
    db.execute.return_value.fetchone.return_value = row

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        result = register_build(request)

    assert result["id"] == 1
    assert result["status"] == "RUNNING"


def test_idempotent_registration():
    request = make_registration()

    row = {
        **request.model_dump(),
        "id": 1,
        "status": "RUNNING",
    }

    db = MagicMock()
    db.execute.return_value.fetchone.side_effect = [
        None,
        row,
    ]

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        result = register_build(request)

    assert result["id"] == 1


def test_registration_metadata_conflict():
    request = make_registration()

    row = {
        **request.model_dump(),
        "git_commit": "b" * 40,
        "id": 1,
    }

    db = MagicMock()
    db.execute.return_value.fetchone.side_effect = [
        None,
        row,
    ]

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        with pytest.raises(HTTPException) as exc:
            register_build(request)

    assert exc.value.status_code == 409


def test_build_not_found():
    db = MagicMock()
    db.execute.return_value.fetchone.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_build_or_404(db, 999)

    assert exc.value.status_code == 404


def test_finalize_running_build():
    db = MagicMock()

    db.execute.return_value.fetchone.side_effect = [
        {"id": 1, "status": "RUNNING"},
        None,
        {"id": 1, "status": "SUCCESS"},
    ]

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        result = finalize_build(
            1,
            BuildFinalization(status="SUCCESS"),
        )

    assert result["status"] == "SUCCESS"
    assert db.execute.call_count == 3


def test_idempotent_finalization():
    db = MagicMock()

    db.execute.return_value.fetchone.return_value = {
        "id": 1,
        "status": "SUCCESS",
    }

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        result = finalize_build(
            1,
            BuildFinalization(status="SUCCESS"),
        )

    assert result["status"] == "SUCCESS"
    assert db.execute.call_count == 1


def test_invalid_status_transition():
    db = MagicMock()

    db.execute.return_value.fetchone.return_value = {
        "id": 1,
        "status": "FAILURE",
    }

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        with pytest.raises(HTTPException) as exc:
            finalize_build(
                1,
                BuildFinalization(status="SUCCESS"),
            )

    assert exc.value.status_code == 409


def test_reject_finalization_with_active_campaign():
    db = MagicMock()

    db.execute.return_value.fetchone.side_effect = [
        {"id": 1, "status": "RUNNING"},
        {"id": 42},
    ]

    with patch("traceability_api.psycopg.connect") as connect:
        connect.return_value.__enter__.return_value = db

        with pytest.raises(HTTPException) as exc:
            finalize_build(
                1,
                BuildFinalization(status="SUCCESS"),
            )

    assert exc.value.status_code == 409
    assert exc.value.detail == "CI build has an active campaign"
    assert db.execute.call_count == 2
