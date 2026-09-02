import json

from sqlalchemy.orm import Session

from app.models.audit import RecoveryAudit
from app.services.logging_service import get_logger

logger = get_logger(__name__)


VALID_OUTCOMES = {
    "succeeded",
    "failed",
    "pending",
    "blocked",
}


def record_recovery_outcome(
    db: Session,
    audit_id: str,
    outcome: str,
    details: dict | None = None,
) -> RecoveryAudit:
    """
    Record the observed outcome of a recovery action.

    This updates the existing immutable recovery identity
    while preserving the original action and idempotency key.
    """

    normalized_outcome = outcome.lower().strip()

    if normalized_outcome not in VALID_OUTCOMES:
        raise ValueError(
            f"Unsupported recovery outcome: {outcome}"
        )

    audit = (
        db.query(RecoveryAudit)
        .filter(
            RecoveryAudit.audit_id == audit_id
        )
        .first()
    )

    if not audit:
        raise ValueError(
            f"Recovery audit not found: {audit_id}"
        )

    existing_result = {}

    if audit.result:
        try:
            existing_result = json.loads(audit.result)
        except json.JSONDecodeError:
            existing_result = {
                "previous_result": audit.result,
            }

    outcome_record = {
        "outcome": normalized_outcome,
        "details": details or {},
    }

    existing_result["outcome"] = outcome_record

    audit.status = normalized_outcome
    audit.result = json.dumps(existing_result)

    db.commit()
    db.refresh(audit)

    logger.info(
        "recovery.outcome_recorded "
        "payment_id=%s audit_id=%s outcome=%s",
        audit.payment_id,
        audit.audit_id,
        normalized_outcome,
    )

    return audit
