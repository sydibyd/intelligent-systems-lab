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


def test_metadata_preserved():
    payload = {
        "number": 42,
        "building": False,
        "result": "FAILURE",
        "timestamp": 1700000000000,
        "duration": 10000,
        "url": "http://jenkins/job/EVAP/42/",
        "actions": [
            {
                "lastBuiltRevision": {
                    "SHA1": "a" * 40
                }
            }
        ],
    }

    client = mock_client(payload)
    state = client.get_build("EVAP", 42)

    assert state.metadata == payload


def test_metadata_requested():
    from urllib.parse import urlsplit, parse_qs

    client = mock_client({
        "number": 42,
        "building": False,
        "result": "SUCCESS",
    })

    client.get_build("EVAP", 42)

    request = client.opener.open.call_args.args[0]
    query = parse_qs(urlsplit(request.full_url).query)

    tree = query["tree"][0]

    assert "timestamp" in tree
    assert "duration" in tree
    assert "url" in tree
    assert "lastBuiltRevision[SHA1]" in tree


def test_explicit_loopback_authentication():
    client = JenkinsClient(
        "http://127.0.0.1:8082",
        "user",
        "token",
        allow_loopback_http=True,
    )

    assert "Authorization" in client.headers


def test_loopback_authentication_disabled_by_default():
    with pytest.raises(ValueError):
        JenkinsClient(
            "http://127.0.0.1:8082",
            "user",
            "token",
        )


def test_remote_http_exception_rejected():
    with pytest.raises(ValueError):
        JenkinsClient(
            "http://jenkins:8080",
            "user",
            "token",
            allow_loopback_http=True,
        )
