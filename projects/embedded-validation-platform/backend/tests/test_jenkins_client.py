import json
from unittest.mock import MagicMock

import pytest

from jenkins_client import JenkinsClient


def mock_client(payload):
    client = JenkinsClient("http://jenkins:8080")

    response = MagicMock()
    response.read.return_value = json.dumps(
        payload
    ).encode()

    client.opener = MagicMock()
    client.opener.open.return_value.__enter__.return_value = (
        response
    )

    return client


def test_completed_build():
    client = mock_client({
        "number": 42,
        "building": False,
        "result": "SUCCESS",
    })

    state = client.get_build("EVAP", 42)

    assert state.reachable
    assert state.building is False
    assert state.result == "SUCCESS"


def test_running_build():
    client = mock_client({
        "number": 42,
        "building": True,
        "result": None,
    })

    state = client.get_build("EVAP", 42)

    assert state.reachable
    assert state.building is True


def test_build_identity_mismatch():
    client = mock_client({
        "number": 99,
        "building": False,
        "result": "SUCCESS",
    })

    assert not client.get_build("EVAP", 42).reachable


def test_jenkins_unavailable():
    client = JenkinsClient("http://jenkins:8080")
    client.opener = MagicMock()
    client.opener.open.side_effect = TimeoutError

    assert not client.get_build("EVAP", 42).reachable


@pytest.mark.parametrize(
    "name", ["", "..", "../EVAP", "folder//EVAP"]
)
def test_invalid_pipeline(name):
    client = JenkinsClient("http://jenkins:8080")

    assert not client.get_build(name, 42).reachable


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://jenkins",
        "http://user:pass@jenkins",
        "http://jenkins?redirect=1",
    ],
)
def test_invalid_base_url(url):
    with pytest.raises(ValueError):
        JenkinsClient(url)


def test_credentials_require_https():
    with pytest.raises(ValueError):
        JenkinsClient(
            "http://jenkins",
            "user",
            "token",
        )


def test_nested_pipeline():
    client = mock_client({
        "number": 42,
        "building": False,
        "result": "SUCCESS",
    })

    client.get_build("folder/EVAP", 42)

    request = client.opener.open.call_args.args[0]

    assert "/job/folder/job/EVAP/42/" in request.full_url


def test_invalid_building_state():
    client = mock_client({
        "number": 42,
        "building": "false",
        "result": "SUCCESS",
    })

    assert not client.get_build("EVAP", 42).reachable
