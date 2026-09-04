import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.recovery import RecoveryExecution
from app.observability import metrics
from app.services.recovery_state_machine import (
    InvalidRecoveryTransition,
    transition_recovery_state,
)


def record_recovery_outcome(
    db: Session,
    *,
    execution_id: int,
    outcome: dict,
) -> RecoveryExecution:
    execution = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.id == execution_id)
        .first()
    )

    if not execution:
        raise ValueError(f"Recovery execution {execution_id} not found")

    success = bool(outcome.get("success", False))
    status = str(outcome.get("status", "")).lower()

    if success:
        target_state = "SUCCEEDED"
    elif status in {"provider_timeout", "provider_error", "provider_unavailable", "failed"}:
        target_state = "FAILED"
    elif status == "blocked":
        target_state = "BLOCKED"
    elif status == "approval_required":
        target_state = "APPROVAL_REQUIRED"
    else:
        target_state = execution.status

    if target_state != execution.status:
        try:
            execution.status = transition_recovery_state(
                execution.status,
                target_state,
            )
        except InvalidRecoveryTransition:
            # Outcome persistence must never silently corrupt the lifecycle.
            raise

    execution.attempt_count = int(execution.attempt_count or 0) + 1
    execution.result = json.dumps(
        {
            "outcome": outcome,
            "recorded_at": datetime.utcnow().isoformat(),
        }
    )
    execution.error = (
        str(outcome.get("error_message"))
        if outcome.get("error_message")
        else None
    )
    execution.updated_at = datetime.utcnow()

    db.add(execution)
    db.commit()
    db.refresh(execution)

    metrics.increment("recovery_outcomes")
    if success:
        metrics.increment("recovery_successes")
    elif target_state == "FAILED":
        metrics.increment("recovery_failures")

    return execution


def build_recovery_feedback(db: Session) -> dict:
    executions = db.query(RecoveryExecution).all()

    total = len(executions)
    succeeded = sum(ex.status == "SUCCEEDED" for ex in executions)
    failed = sum(ex.status == "FAILED" for ex in executions)
    blocked = sum(ex.status == "BLOCKED" for ex in executions)
    approval_required = sum(
        ex.status == "APPROVAL_REQUIRED" for ex in executions
    )

    completed = succeeded + failed
    success_rate = succeeded / completed if completed else 0.0

    return {
        "total_executions": total,
        "succeeded": succeeded,
        "failed": failed,
        "blocked": blocked,
        "approval_required": approval_required,
        "completed": completed,
        "success_rate": round(success_rate, 4),
    }
