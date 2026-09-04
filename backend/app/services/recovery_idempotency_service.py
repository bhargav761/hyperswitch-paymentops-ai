from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.recovery import RecoveryExecution
from app.recovery.idempotency import build_recovery_key


def claim_recovery(
    db: Session,
    *,
    payment_id: str,
    action: str,
    connector: str | None = None,
    confidence: float | None = None,
) -> tuple[RecoveryExecution, bool]:
    key = build_recovery_key(payment_id, action)

    existing = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.idempotency_key == key)
        .first()
    )

    if existing:
        return existing, False

    execution = RecoveryExecution(
        payment_id=payment_id,
        idempotency_key=key,
        action=action,
        status="CLAIMED",
        connector=connector,
        confidence=confidence,
        attempt_count=0,
    )

    db.add(execution)

    try:
        db.commit()
        db.refresh(execution)
        return execution, True
    except IntegrityError:
        db.rollback()
        existing = (
            db.query(RecoveryExecution)
            .filter(RecoveryExecution.idempotency_key == key)
            .first()
        )
        if existing:
            return existing, False
        raise
