import json

import pytest

from app.models.recovery import RecoveryExecution
from app.services.recovery_outcome_service import (
    build_recovery_feedback,
    record_recovery_outcome,
)
from app.services.recovery_state_machine import InvalidRecoveryTransition


def _execution(db, status="EXECUTING"):
    execution = RecoveryExecution(
        payment_id="pay_outcome_001",
        idempotency_key=f"outcome:{status}",
        action="RETRY_NOW",
        status=status,
        connector="stripe",
        confidence=0.9,
        attempt_count=0,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    return execution


def test_successful_outcome_persists(db_session):
    execution = _execution(db_session)

    result = record_recovery_outcome(
        db_session,
        execution_id=execution.id,
        outcome={
            "status": "succeeded",
            "success": True,
            "provider_reference": "ref-001",
        },
    )

    assert result.status == "SUCCEEDED"
    assert result.attempt_count == 1

    payload = json.loads(result.result)
    assert payload["outcome"]["provider_reference"] == "ref-001"


def test_failed_provider_outcome_persists(db_session):
    execution = _execution(db_session)

    result = record_recovery_outcome(
        db_session,
        execution_id=execution.id,
        outcome={
            "status": "provider_timeout",
            "success": False,
            "error_message": "provider timed out",
        },
    )

    assert result.status == "FAILED"
    assert result.attempt_count == 1
    assert result.error == "provider timed out"


def test_invalid_lifecycle_transition_is_rejected(db_session):
    execution = _execution(db_session, status="SUCCEEDED")

    with pytest.raises(InvalidRecoveryTransition):
        record_recovery_outcome(
            db_session,
            execution_id=execution.id,
            outcome={
                "status": "failed",
                "success": False,
            },
        )


def test_feedback_aggregates_outcomes(db_session):
    _execution(db_session, "SUCCEEDED")
    _execution(db_session, "FAILED")
    _execution(db_session, "BLOCKED")
    _execution(db_session, "APPROVAL_REQUIRED")

    feedback = build_recovery_feedback(db_session)

    assert feedback["total_executions"] == 4
    assert feedback["succeeded"] == 1
    assert feedback["failed"] == 1
    assert feedback["blocked"] == 1
    assert feedback["approval_required"] == 1
    assert feedback["completed"] == 2
    assert feedback["success_rate"] == 0.5


def test_feedback_handles_no_completed_recoveries(db_session):
    feedback = build_recovery_feedback(db_session)

    assert feedback["total_executions"] == 0
    assert feedback["completed"] == 0
    assert feedback["success_rate"] == 0.0
