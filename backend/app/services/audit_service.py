import json
import uuid

from sqlalchemy.orm import Session

from app.models.audit import RecoveryAudit
from app.recovery.idempotency import build_recovery_key
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def create_recovery_audit(
    db: Session,
    payment_id: str,
    action: str,
    status: str,
    reason: str,
    confidence: float,
    result: dict,
) -> RecoveryAudit:

    idempotency_key = build_recovery_key(
        payment_id,
        action,
    )

    existing = (
        db.query(RecoveryAudit)
        .filter(
            RecoveryAudit.idempotency_key
            == idempotency_key
        )
        .first()
    )

    if existing:
        logger.info(
            "recovery.audit_duplicate payment_id=%s key=%s",
            payment_id,
            idempotency_key,
        )
        return existing

    audit = RecoveryAudit(
        audit_id=f"audit_{uuid.uuid4().hex}",
        payment_id=payment_id,
        idempotency_key=idempotency_key,
        action=action,
        status=status,
        reason=reason,
        confidence=confidence,
        result=json.dumps(result),
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    logger.info(
        "recovery.audit_created payment_id=%s audit_id=%s action=%s",
        payment_id,
        audit.audit_id,
        action,
    )

    return audit
