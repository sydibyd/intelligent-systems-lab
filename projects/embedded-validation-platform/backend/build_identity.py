from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IdentityVerification:
    verified: bool
    reason: str


def verify_build_identity(
    build: dict,
    observed: dict,
) -> IdentityVerification:

    if (
        type(observed.get("number")) is not int
        or observed["number"] != build["build_number"]
    ):
        return IdentityVerification(
            False, "BUILD_NUMBER_MISMATCH"
        )

    if (
        not build.get("build_url")
        or observed.get("url") != build["build_url"]
    ):
        return IdentityVerification(
            False, "BUILD_URL_MISMATCH"
        )

    actions = observed.get("actions")

    if not isinstance(actions, list):
        return IdentityVerification(
            False, "GIT_METADATA_MISSING"
        )

    commits = set()

    for action in actions:
        if not isinstance(action, dict):
            continue

        revision = action.get("lastBuiltRevision")

        if isinstance(revision, dict):
            sha = revision.get("SHA1")

            if isinstance(sha, str):
                commits.add(sha.lower())

    if not commits:
        return IdentityVerification(
            False, "GIT_METADATA_MISSING"
        )

    if commits != {build["git_commit"].lower()}:
        return IdentityVerification(
            False, "GIT_COMMIT_MISMATCH_OR_AMBIGUOUS"
        )

    timestamp = observed.get("timestamp")
    duration = observed.get("duration")
    created_at = build.get("created_at")

    if (
        type(timestamp) is not int
        or timestamp <= 0
        or type(duration) is not int
        or duration < 0
        or not isinstance(created_at, datetime)
        or created_at.utcoffset() is None
    ):
        return IdentityVerification(
            False, "INVALID_TEMPORAL_METADATA"
        )

    delay = created_at.timestamp() - timestamp / 1000

    if not -2 <= delay <= duration / 1000 + 2:
        return IdentityVerification(
            False, "BUILD_TIMESTAMP_MISMATCH"
        )

    return IdentityVerification(
        True, "BUILD_IDENTITY_VERIFIED"
    )
