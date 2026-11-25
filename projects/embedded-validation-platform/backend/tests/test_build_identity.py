from datetime import datetime, timezone

import pytest

from build_identity import verify_build_identity


SHA = "a" * 40


@pytest.fixture
def build():
    return {
        "build_number": 5,
        "build_url": "http://jenkins/job/EVAP/5/",
        "git_commit": SHA,
        "created_at": datetime.fromtimestamp(
            1700000003, timezone.utc
        ),
    }


@pytest.fixture
def observed():
    return {
        "number": 5,
        "url": "http://jenkins/job/EVAP/5/",
        "timestamp": 1700000000000,
        "duration": 10000,
        "actions": [
            {
                "lastBuiltRevision": {
                    "SHA1": SHA
                }
            }
        ],
    }


def test_verified_identity(build, observed):
    result = verify_build_identity(build, observed)
    assert result.verified


@pytest.mark.parametrize(
    "field,value,reason",
    [
        (
            "number", 6,
            "BUILD_NUMBER_MISMATCH"
        ),
        (
            "url", "http://other/job/EVAP/5/",
            "BUILD_URL_MISMATCH"
        ),
        (
            "actions", [],
            "GIT_METADATA_MISSING"
        ),
        (
            "actions",
            [{"lastBuiltRevision": {"SHA1": "b" * 40}}],
            "GIT_COMMIT_MISMATCH_OR_AMBIGUOUS"
        ),
        (
            "timestamp", 1700001000000,
            "BUILD_TIMESTAMP_MISMATCH"
        ),
        (
            "timestamp", 1699999000000,
            "BUILD_TIMESTAMP_MISMATCH"
        ),
        (
            "timestamp", None,
            "INVALID_TEMPORAL_METADATA"
        ),
        (
            "duration", -1,
            "INVALID_TEMPORAL_METADATA"
        ),
    ],
)
def test_identity_rejected(
    build, observed, field, value, reason
):
    observed[field] = value

    result = verify_build_identity(build, observed)

    assert not result.verified
    assert result.reason == reason


def test_ambiguous_git_commits(build, observed):
    observed["actions"].append({
        "lastBuiltRevision": {
            "SHA1": "b" * 40
        }
    })

    result = verify_build_identity(build, observed)

    assert not result.verified
