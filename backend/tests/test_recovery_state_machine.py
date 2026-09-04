import pytest

from app.services.recovery_state_machine import (
    InvalidRecoveryTransition,
    RecoveryState,
    allowed_recovery_transitions,
    can_transition,
    transition_recovery_state,
)


def test_planned_can_be_claimed():
    assert can_transition(RecoveryState.PLANNED, RecoveryState.CLAIMED)
    assert transition_recovery_state("PLANNED", "CLAIMED") == "CLAIMED"


def test_approval_lifecycle():
    assert can_transition("PLANNED", "APPROVAL_REQUIRED")
    assert can_transition("APPROVAL_REQUIRED", "APPROVED")
    assert can_transition("APPROVED", "EXECUTING")


def test_execution_terminal_outcomes():
    assert can_transition("EXECUTING", "SUCCEEDED")
    assert can_transition("EXECUTING", "FAILED")
    assert not can_transition("SUCCEEDED", "EXECUTING")
    assert not can_transition("BLOCKED", "EXECUTING")


def test_invalid_transition_raises():
    with pytest.raises(InvalidRecoveryTransition):
        transition_recovery_state("PLANNED", "SUCCEEDED")


def test_failed_recovery_can_be_reclaimed():
    assert can_transition("FAILED", "CLAIMED")
    assert can_transition("FAILED", "BLOCKED")


def test_allowed_transitions_are_explicit():
    assert set(allowed_recovery_transitions("EXECUTING")) == {
        "SUCCEEDED",
        "FAILED",
    }
