from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.approval import RecoveryApproval
from app.services.approval_service import (
    create_or_get_approval,
    decide_approval,
)

router = APIRouter(
    prefix="/api/v1/approvals",
    tags=["approvals"],
)


class ApprovalRequest(BaseModel):
    action: str = Field(min_length=1, max_length=100)
    reason: str = Field(min_length=1, max_length=1000)
    confidence: float = Field(ge=0.0, le=1.0)


class ApprovalDecision(BaseModel):
    approved: bool
    approved_by: str = Field(min_length=1, max_length=100)


@router.get("/{payment_id}")
def get_approval(
    payment_id: str,
    db: Session = Depends(get_db),
):
    approval = (
        db.query(RecoveryApproval)
        .filter(RecoveryApproval.payment_id == payment_id)
        .order_by(RecoveryApproval.created_at.desc())
        .first()
    )

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Approval not found",
        )

    return {
        "approval_id": approval.approval_id,
        "payment_id": approval.payment_id,
        "action": approval.action,
        "status": approval.status,
        "reason": approval.reason,
        "confidence": approval.confidence,
        "requested_by": approval.requested_by,
        "approved_by": approval.approved_by,
        "created_at": approval.created_at,
        "decided_at": approval.decided_at,
    }


@router.post("/{payment_id}/request")
def request_approval(
    payment_id: str,
    action: str = Query(..., min_length=1, max_length=100),
    reason: str = Query(..., min_length=1, max_length=1000),
    confidence: float = Query(..., ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    approval = create_or_get_approval(
        db=db,
        payment_id=payment_id,
        action=action,
        reason=reason,
        confidence=confidence,
    )

    return {
        "approval_id": approval.approval_id,
        "payment_id": approval.payment_id,
        "action": approval.action,
        "status": approval.status,
        "idempotency_key": approval.idempotency_key,
    }


@router.post("/{payment_id}/decide")
def approve_or_reject(
    payment_id: str,
    decision: ApprovalDecision,
    db: Session = Depends(get_db),
):
    approval = (
        db.query(RecoveryApproval)
        .filter(RecoveryApproval.payment_id == payment_id)
        .order_by(RecoveryApproval.created_at.desc())
        .first()
    )

    if not approval:
        raise HTTPException(
            status_code=404,
            detail="Approval not found",
        )

    approval = decide_approval(
        db=db,
        approval=approval,
        approved=decision.approved,
        approved_by=decision.approved_by,
    )

    return {
        "approval_id": approval.approval_id,
        "payment_id": approval.payment_id,
        "action": approval.action,
        "status": approval.status,
        "approved_by": approval.approved_by,
        "decided_at": approval.decided_at,
    }
