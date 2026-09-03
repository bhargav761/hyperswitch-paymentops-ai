import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.approval import RecoveryApproval
from app.recovery.idempotency import build_recovery_key
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def create_or_get_approval(
    *,
    db: Session,
    payment_id: str,
    action: str,
    reason: str,
    confidence: float,
) -> RecoveryApproval:
    idempotency_key = build_recovery_key(payment_id, action)

    existing = (
        db.query(RecoveryApproval)
        .filter(
            RecoveryApproval.idempotency_key == idempotency_key
        )
        .first()
    )

    if existing:
        return existing

    approval = RecoveryApproval(
        approval_id=f"approval_{uuid.uuid4().hex}",
        payment_id=payment_id,
        action=action,
        idempotency_key=idempotency_key,
        status="PENDING",
        reason=reason,
        confidence=confidence,
        requested_by="paymentops-ai",
    )

    db.add(approval)
    db.commit()
    db.refresh(approval)

    logger.info(
        "recovery.approval_created payment_id=%s approval_id=%s",
        payment_id,
        approval.approval_id,
    )

    return approval


def decide_approval(
    *,
    db: Session,
    approval: RecoveryApproval,
    approved: bool,
    approved_by: str,
) -> RecoveryApproval:
    if approval.status != "PENDING":
        return approval

    approval.status = "APPROVED" if approved else "REJECTED"
    approval.approved_by = approved_by
    approval.decided_at = datetime.utcnow()

    db.commit()
    db.refresh(approval)

    logger.info(
        "recovery.approval_decided approval_id=%s status=%s actor=%s",
        approval.approval_id,
        approval.status,
        approved_by,
    )

    return approval
