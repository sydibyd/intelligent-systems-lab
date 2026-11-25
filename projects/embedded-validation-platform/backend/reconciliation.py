from dataclasses import dataclass
from enum import Enum


TERMINAL_STATUSES = frozenset({
    "SUCCESS",
    "FAILURE",
    "ABORTED",
    "UNSTABLE",
    "INTERRUPTED",
    "NOT_BUILT",
})


class Action(str, Enum):
    FINALIZE = "FINALIZE"
    KEEP_RUNNING = "KEEP_RUNNING"
    DEFER = "DEFER"
    NO_CHANGE = "NO_CHANGE"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class Decision:
    action: Action
    reason: str
    target_status: str | None = None


def evaluate_build(
    current_status: str,
    jenkins_reachable: bool,
    jenkins_building: bool | None,
    jenkins_result: str | None,
    active_campaign: bool,
) -> Decision:

    if current_status not in TERMINAL_STATUSES | {"RUNNING"}:
        return Decision(
            Action.DEFER,
            "INVALID_DATABASE_STATUS",
        )

    if not jenkins_reachable:
        return Decision(
            Action.DEFER,
            "JENKINS_UNAVAILABLE",
        )

    if jenkins_building is True:
        if current_status != "RUNNING":
            return Decision(
                Action.CONFLICT,
                "DATABASE_FINALIZED_JENKINS_RUNNING",
            )

        return Decision(
            Action.KEEP_RUNNING,
            "JENKINS_BUILD_ACTIVE",
        )

    if jenkins_building is not False:
        return Decision(
            Action.DEFER,
            "UNKNOWN_JENKINS_STATE",
        )

    if jenkins_result not in TERMINAL_STATUSES:
        return Decision(
            Action.DEFER,
            "INVALID_JENKINS_RESULT",
        )

    if current_status in TERMINAL_STATUSES:
        if current_status == jenkins_result:
            return Decision(
                Action.NO_CHANGE,
                "ALREADY_FINALIZED",
            )

        return Decision(
            Action.CONFLICT,
            "TERMINAL_STATUS_MISMATCH",
        )

    if active_campaign:
        return Decision(
            Action.DEFER,
            "ACTIVE_CAMPAIGN",
        )

    return Decision(
        Action.FINALIZE,
        "JENKINS_TERMINAL_CONFIRMED",
        target_status=jenkins_result,
    )
