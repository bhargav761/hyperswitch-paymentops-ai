import uuid

from sqlalchemy.orm import Session

from app.models.audit import RecoveryAudit
from app.models.reconciliation import RecoveryReconciliation
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def determine_reconciliation_status(
    *,
    expected_status: str,
    observed_status: str,
) -> tuple[str, str]:
    expected = expected_status.lower().strip()
    observed = observed_status.lower().strip()

    if observed == "pending":
        return "PENDING", "Provider payment remains pending."

    if observed == "blocked":
        return "PENDING", "Payment remains blocked and requires follow-up."

    if expected == observed:
        return "MATCHED", (
            "Observed provider status matches the expected recovery outcome."
        )

    return "MISMATCH", (
        "Observed provider status does not match the expected recovery outcome."
    )


def reconcile_recovery_outcome(
    *,
    db: Session,
    payment_id: str,
    provider_event_id: str,
    observed_status: str,
    expected_status: str = "succeeded",
) -> RecoveryReconciliation | None:
    """
    Reconcile a provider-observed payment status against the expected
    recovery outcome.

    The provider event ID is the idempotency boundary for reconciliation.
    """

    existing = (
        db.query(RecoveryReconciliation)
        .filter(
            RecoveryReconciliation.provider_event_id
            == provider_event_id
        )
        .first()
    )

    if existing:
        logger.info(
            "recovery.reconciliation_duplicate "
            "payment_id=%s provider_event_id=%s "
            "reconciliation_id=%s",
            payment_id,
            provider_event_id,
            existing.reconciliation_id,
        )
        return existing

    audit = (
        db.query(RecoveryAudit)
        .filter(
            RecoveryAudit.payment_id == payment_id,
            RecoveryAudit.action != "HUMAN_REVIEW",
        )
        .order_by(RecoveryAudit.created_at.desc())
        .first()
    )

    if not audit:
        logger.info(
            "recovery.reconciliation_skipped "
            "payment_id=%s provider_event_id=%s reason=no_recovery_audit",
            payment_id,
            provider_event_id,
        )
        return None

    status, reason = determine_reconciliation_status(
        expected_status=expected_status,
        observed_status=observed_status,
    )

    reconciliation = RecoveryReconciliation(
        reconciliation_id=f"recon_{uuid.uuid4().hex}",
        payment_id=payment_id,
        audit_id=audit.audit_id,
        provider_event_id=provider_event_id,
        expected_status=expected_status.lower().strip(),
        observed_status=observed_status.lower().strip(),
        status=status,
        reason=reason,
    )

    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)

    logger.info(
        "recovery.reconciliation_created "
        "payment_id=%s audit_id=%s provider_event_id=%s "
        "status=%s expected=%s observed=%s",
        payment_id,
        audit.audit_id,
        provider_event_id,
        status,
        expected_status,
        observed_status,
    )

    return reconciliation
