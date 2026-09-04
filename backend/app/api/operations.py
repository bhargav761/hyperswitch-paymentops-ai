from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.audit import RecoveryAudit
from app.models.payment import Payment
from app.models.recovery import RecoveryExecution
from app.observability import metrics
from app.routing.circuit_breaker import circuit_breaker
from app.services.recovery_outcome_service import build_recovery_feedback

router = APIRouter(
    prefix="/api/v1/operations",
    tags=["operations"],
)


@router.get("/recoveries/{payment_id}")
def recovery_status(
    payment_id: str,
    db: Session = Depends(get_db),
):
    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    executions = (
        db.query(RecoveryExecution)
        .filter(RecoveryExecution.payment_id == payment_id)
        .order_by(RecoveryExecution.created_at.desc())
        .all()
    )

    return {
        "payment_id": payment_id,
        "count": len(executions),
        "recoveries": [
            {
                "id": execution.id,
                "action": execution.action,
                "status": execution.status,
                "connector": execution.connector,
                "confidence": execution.confidence,
                "attempt_count": execution.attempt_count,
                "idempotency_key": execution.idempotency_key,
                "created_at": execution.created_at,
                "updated_at": execution.updated_at,
            }
            for execution in executions
        ],
    }


@router.get("/feedback")
def recovery_feedback(db: Session = Depends(get_db)):
    return build_recovery_feedback(db)


@router.get("/circuits")
def circuit_status():
    return {
        "circuits": circuit_breaker.snapshot(),
    }


@router.get("/metrics")
def operational_metrics():
    return {
        "counters": metrics.snapshot(),
        "circuits": circuit_breaker.snapshot(),
    }


@router.get("/audits/{payment_id}")
def recovery_audits(
    payment_id: str,
    db: Session = Depends(get_db),
):
    audits = (
        db.query(RecoveryAudit)
        .filter(RecoveryAudit.payment_id == payment_id)
        .order_by(RecoveryAudit.created_at.desc())
        .all()
    )

    return {
        "payment_id": payment_id,
        "count": len(audits),
        "audits": [
            {
                "audit_id": audit.audit_id,
                "action": audit.action,
                "status": audit.status,
                "reason": audit.reason,
                "confidence": audit.confidence,
                "idempotency_key": audit.idempotency_key,
                "created_at": audit.created_at,
            }
            for audit in audits
        ],
    }
