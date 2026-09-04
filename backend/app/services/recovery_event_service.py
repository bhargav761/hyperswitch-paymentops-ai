import json
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.recovery import RecoveryExecution
from app.services.incident_service import analyze_payment
from app.services.logging_service import get_logger

logger = get_logger(__name__)


RECOVERY_ELIGIBLE_STATUSES = {"failed", "failure", "declined", "pending"}


def dispatch_recovery_event(
    db: Session,
    payment,
    event_id: str,
) -> RecoveryExecution | None:
    status = (payment.status or "").lower()

    if status not in RECOVERY_ELIGIBLE_STATUSES:
        return None

    idempotency_key = f"recovery-event:{event_id}"

    existing = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.idempotency_key == idempotency_key)
        .first()
    )

    if existing:
        return existing

    incident = analyze_payment(payment)

    execution = RecoveryExecution(
        payment_id=payment.payment_id,
        idempotency_key=idempotency_key,
        action=incident["recommended_action"],
        status="PLANNED",
        connector=payment.connector,
        confidence=None,
        attempt_count=0,
        result=json.dumps(
            {
                "event_id": event_id,
                "root_cause": incident["root_cause"],
                "severity": incident["severity"],
                "risk_score": incident["risk_score"],
                "recovery_priority": incident["recovery_priority"],
                "signals": incident["signals"],
                "created_at": datetime.utcnow().isoformat(),
            }
        ),
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    logger.info(
        "recovery.event_dispatched payment_id=%s "
        "event_id=%s recovery_id=%s action=%s",
        payment.payment_id,
        event_id,
        execution.id,
        execution.action,
    )

    return execution
