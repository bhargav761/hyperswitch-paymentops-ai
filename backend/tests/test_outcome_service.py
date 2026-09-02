import json

import pytest

from app.models.audit import RecoveryAudit
from app.services.outcome_service import record_recovery_outcome


def create_audit(db):
    audit = RecoveryAudit(
        audit_id="audit_p36_001",
        payment_id="pay_p36_001",
        idempotency_key="recovery:pay_p36_001:RETRY_NOW",
        action="RETRY_NOW",
        status="authorized",
        reason="Controlled retry authorized.",
        confidence=0.90,
        result=json.dumps(
            {
                "execution": {
                    "executed": False,
                    "status": "authorized",
                }
            }
        ),
    )

    db.add(audit)
    db.commit()
    db.refresh(audit)

    return audit


def test_record_successful_recovery_outcome(db_session):
    audit = create_audit(db_session)

    updated = record_recovery_outcome(
        db=db_session,
        audit_id=audit.audit_id,
        outcome="succeeded",
        details={
            "connector": "razorpay",
            "latency_ms": 1200,
        },
    )

    assert updated.status == "succeeded"

    result = json.loads(updated.result)

    assert result["outcome"]["outcome"] == "succeeded"
    assert result["outcome"]["details"]["connector"] == "razorpay"


def test_record_failed_recovery_outcome(db_session):
    audit = create_audit(db_session)

    updated = record_recovery_outcome(
        db=db_session,
        audit_id=audit.audit_id,
        outcome="failed",
        details={
            "reason": "connector_unavailable",
        },
    )

    assert updated.status == "failed"

    result = json.loads(updated.result)

    assert result["outcome"]["outcome"] == "failed"
    assert (
        result["outcome"]["details"]["reason"]
        == "connector_unavailable"
    )


def test_record_pending_outcome(db_session):
    audit = create_audit(db_session)

    updated = record_recovery_outcome(
        db=db_session,
        audit_id=audit.audit_id,
        outcome="pending",
    )

    assert updated.status == "pending"

    result = json.loads(updated.result)

    assert result["outcome"]["outcome"] == "pending"
    assert result["outcome"]["details"] == {}


def test_invalid_outcome_is_rejected(db_session):
    audit = create_audit(db_session)

    with pytest.raises(ValueError, match="Unsupported recovery outcome"):
        record_recovery_outcome(
            db=db_session,
            audit_id=audit.audit_id,
            outcome="unknown",
        )


def test_missing_audit_is_rejected(db_session):
    with pytest.raises(ValueError, match="Recovery audit not found"):
        record_recovery_outcome(
            db=db_session,
            audit_id="audit_does_not_exist",
            outcome="succeeded",
        )
