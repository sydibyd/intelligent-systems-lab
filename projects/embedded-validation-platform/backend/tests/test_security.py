import hashlib
import json

import pytest

from security import authenticate, allowed, load_identities

TOKEN = "a" * 48


def records():
    return [{"name": "viewer1", "role": "viewer",
             "digest": hashlib.sha256(TOKEN.encode()).hexdigest()}]


def test_valid_token():
    identities = load_identities(json.dumps(records()))
    assert authenticate("Bearer " + TOKEN, identities).role == "viewer"


@pytest.mark.parametrize("header", ["", "Basic " + TOKEN, "Bearer wrong", "Bearer " + "b" * 48])
def test_invalid_token(header):
    assert authenticate(header, load_identities(json.dumps(records()))) is None


def test_duplicate_identity():
    with pytest.raises(ValueError):
        load_identities(json.dumps(records() * 2))


@pytest.mark.parametrize("role,method,path,expected", [
    ("viewer", "GET", "/api/dashboard", True),
    ("viewer", "POST", "/api/campaigns", False),
    ("engineer", "POST", "/api/campaigns", True),
    ("architect", "POST", "/api/requirements/import", True),
    ("ci", "POST", "/api/requirements/import", False),
    ("ci", "POST", "/api/ci-builds", True),
    ("admin", "POST", "/api/ci-builds", False),
    ("ci", "PATCH", "/api/ci-builds/1", True),
    ("admin", "DELETE", "/api/requirements", False),
    ("unknown", "GET", "/api/dashboard", False),
])
def test_permissions(role, method, path, expected):
    assert allowed(role, method, path) is expected
