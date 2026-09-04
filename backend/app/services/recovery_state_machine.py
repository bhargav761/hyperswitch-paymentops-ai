from enum import Enum


class RecoveryState(str, Enum):
    PLANNED = "PLANNED"
    CLAIMED = "CLAIMED"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


_ALLOWED_TRANSITIONS = {
    RecoveryState.PLANNED: {
        RecoveryState.CLAIMED,
        RecoveryState.APPROVAL_REQUIRED,
        RecoveryState.BLOCKED,
    },
    RecoveryState.CLAIMED: {
        RecoveryState.APPROVAL_REQUIRED,
        RecoveryState.APPROVED,
        RecoveryState.EXECUTING,
        RecoveryState.BLOCKED,
    },
    RecoveryState.APPROVAL_REQUIRED: {
        RecoveryState.APPROVED,
        RecoveryState.BLOCKED,
    },
    RecoveryState.APPROVED: {
        RecoveryState.EXECUTING,
        RecoveryState.BLOCKED,
    },
    RecoveryState.EXECUTING: {
        RecoveryState.SUCCEEDED,
        RecoveryState.FAILED,
    },
    RecoveryState.SUCCEEDED: set(),
    RecoveryState.FAILED: {
        RecoveryState.CLAIMED,
        RecoveryState.BLOCKED,
    },
    RecoveryState.BLOCKED: set(),
}


class InvalidRecoveryTransition(ValueError):
    pass


def can_transition(current: str | RecoveryState, target: str | RecoveryState) -> bool:
    current_state = RecoveryState(current)
    target_state = RecoveryState(target)
    return target_state in _ALLOWED_TRANSITIONS[current_state]


def transition_recovery_state(
    current: str | RecoveryState,
    target: str | RecoveryState,
) -> str:
    current_state = RecoveryState(current)
    target_state = RecoveryState(target)

    if not can_transition(current_state, target_state):
        raise InvalidRecoveryTransition(
            f"Invalid recovery transition: "
            f"{current_state.value} -> {target_state.value}"
        )

    return target_state.value


def allowed_recovery_transitions(
    current: str | RecoveryState,
) -> tuple[str, ...]:
    current_state = RecoveryState(current)
    return tuple(state.value for state in _ALLOWED_TRANSITIONS[current_state])
