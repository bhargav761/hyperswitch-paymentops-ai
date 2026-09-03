from app.config.settings import (
    HYPERSWITCH_API_KEY,
    HYPERSWITCH_BASE_URL,
    HYPERSWITCH_TIMEOUT_SECONDS,
)
from app.services.recovery_execution_service import (
    build_hyperswitch_adapter,
    execute_policy_approved_recovery,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.audit import RecoveryAudit
from app.models.payment import Payment
from app.recovery.actions import prepare_recovery_action
from app.recovery.decision_engine import decide_recovery
from app.recovery.next_best_action import build_next_best_action
from app.recovery.policy_gateway import evaluate_policy_gate
from app.services.audit_service import create_recovery_audit
from app.services.approval_service import create_or_get_approval
from app.services.incident_service import analyze_payment
from app.routing.health_score import calculate_connector_health
from app.routing.route_decision import decide_route
from app.ai.agent import analyze_payment as analyze_payment_with_ai

router = APIRouter(
    prefix="/api/v1/recovery",
    tags=["recovery"],
)


@router.get("/plan/{payment_id}")
def recovery_plan(
    payment_id: str,
    db: Session = Depends(get_db),
):
    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    incident = analyze_payment(payment)

    decision = decide_recovery(
        amount=float(payment.amount),
        root_cause=incident["root_cause"],
        risk_score=incident["risk_score"],
    )

    execution = prepare_recovery_action(decision)

    next_best_action = build_next_best_action(
        recovery_action=decision.action,
        confidence=decision.confidence,
        reason=decision.reason,
        requires_approval=decision.requires_approval,
        root_cause=incident["root_cause"],
        risk_score=incident["risk_score"],
    )

    policy = evaluate_policy_gate(
        payment_id=payment.payment_id,
        amount=float(payment.amount),
        action=next_best_action.action,
        confidence=next_best_action.confidence,
        retry_count=0,
    )

    if policy.decision == "DENY":
        execution = {
            **execution,
            "executed": False,
            "status": "blocked",
            "message": "Recovery action blocked by policy.",
        }
    elif policy.decision == "APPROVAL_REQUIRED":
        execution = {
            **execution,
            "executed": False,
            "status": "approval_required",
            "message": "Recovery action requires human approval.",
        }
    else:
        execution = {
            **execution,
            "status": "authorized",
            "message": (
                "Recovery action passed policy validation "
                "but external payment execution is not enabled."
            ),
        }

    audit = create_recovery_audit(
        db=db,
        payment_id=payment.payment_id,
        action=next_best_action.action,
        status=execution["status"],
        reason=next_best_action.reason,
        confidence=next_best_action.confidence,
        result={
            "execution": execution,
            "policy": {
                "decision": policy.decision,
                "allowed": policy.allowed,
                "requires_approval": policy.requires_approval,
                "reason_codes": list(policy.reason_codes),
            },
        },
    )

    return {
        "payment_id": payment.payment_id,
        "incident": incident,
        "decision": {
            "action": decision.action,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "requires_approval": decision.requires_approval,
        },
        "execution": execution,
        "next_best_action": {
            "action": next_best_action.action,
            "confidence": next_best_action.confidence,
            "reason": next_best_action.reason,
            "requires_approval": next_best_action.requires_approval,
            "delay_seconds": next_best_action.delay_seconds,
            "reason_codes": list(next_best_action.reason_codes),
        },
        "policy": {
            "decision": policy.decision,
            "allowed": policy.allowed,
            "requires_approval": policy.requires_approval,
            "idempotency_key": policy.idempotency_key,
            "reason_codes": list(policy.reason_codes),
        },
        "audit": {
            "audit_id": audit.audit_id,
            "idempotency_key": audit.idempotency_key,
            "status": audit.status,
        },
    }
@router.post("/execute/{payment_id}")
def execute_recovery(
    payment_id: str,
    db: Session = Depends(get_db),
):
    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    incident = analyze_payment(payment)

    decision = decide_recovery(
        amount=float(payment.amount),
        root_cause=incident["root_cause"],
        risk_score=incident["risk_score"],
    )

    next_best_action = build_next_best_action(
        recovery_action=decision.action,
        confidence=decision.confidence,
        reason=decision.reason,
        requires_approval=decision.requires_approval,
        root_cause=incident["root_cause"],
        risk_score=incident["risk_score"],
    )

    policy = evaluate_policy_gate(
        payment_id=payment.payment_id,
        amount=float(payment.amount),
        action=next_best_action.action,
        confidence=next_best_action.confidence,
        retry_count=0,
    )

    ai_analysis = analyze_payment_with_ai(
        status=payment.status,
        failure_code=payment.failure_code,
        failure_reason=payment.failure_reason,
        recommended_action=next_best_action.action,
    )

    # Build a deterministic routing view from the payment's current
    # connector. Provider telemetry can replace these inputs later.
    current_connector = payment.connector or "default"

    connector_health = {
        current_connector: calculate_connector_health(
            success_rate=0.95 if payment.status != "failed" else 0.70,
            latency_ms=float(payment.latency_ms or 500),
            failure_rate=0.05 if payment.status != "failed" else 0.30,
        ),
    }

    connectors = [
        {
            "name": name,
            "health_score": score,
            "latency_ms": float(payment.latency_ms or 500),
            "enabled": True,
        }
        for name, score in connector_health.items()
    ]

    route = decide_route(
        connectors=connectors,
        current_connector=current_connector,
        failure_code=payment.failure_code,
    )

    selected_connector = route["connector"] or current_connector

    approval = None

    if policy.decision == "APPROVAL_REQUIRED":
        approval = create_or_get_approval(
            db=db,
            payment_id=payment.payment_id,
            action=policy.action,
            reason=next_best_action.reason,
            confidence=next_best_action.confidence,
        )

        execution = {
            "executed": False,
            "status": "approval_required",
            "action": policy.action,
            "message": "Recovery action requires human approval.",
            "idempotency_key": policy.idempotency_key,
        }
    else:
        adapter = build_hyperswitch_adapter(
            base_url=HYPERSWITCH_BASE_URL,
            api_key=HYPERSWITCH_API_KEY,
            timeout_seconds=HYPERSWITCH_TIMEOUT_SECONDS,
        )

        execution = execute_policy_approved_recovery(
            policy=policy,
            payment_id=payment.payment_id,
            amount=float(payment.amount),
            currency=payment.currency,
            payment_method=payment.method,
            connector=selected_connector,
            adapter=adapter,
        )

    audit = create_recovery_audit(
        db=db,
        payment_id=payment.payment_id,
        action=next_best_action.action,
        status=execution["status"],
        reason=next_best_action.reason,
        confidence=next_best_action.confidence,
        result={
            "execution": execution,
            "policy": {
                "decision": policy.decision,
                "allowed": policy.allowed,
                "requires_approval": policy.requires_approval,
                "reason_codes": list(policy.reason_codes),
            },
        },
    )

    return {
        "payment_id": payment.payment_id,
        "incident": incident,
        "decision": {
            "action": decision.action,
            "confidence": decision.confidence,
            "reason": decision.reason,
            "requires_approval": decision.requires_approval,
        },
        "next_best_action": {
            "action": next_best_action.action,
            "confidence": next_best_action.confidence,
            "reason": next_best_action.reason,
            "requires_approval": next_best_action.requires_approval,
            "delay_seconds": next_best_action.delay_seconds,
            "reason_codes": list(next_best_action.reason_codes),
        },
        "policy": {
            "decision": policy.decision,
            "allowed": policy.allowed,
            "requires_approval": policy.requires_approval,
            "idempotency_key": policy.idempotency_key,
            "reason_codes": list(policy.reason_codes),
        },
        "ai_analysis": ai_analysis,
        "routing": {
            "decision": route["decision"],
            "connector": route["connector"],
            "reason": route["reason"],
            "health_scores": connector_health,
        },
        "execution": execution,
        "approval": (
            {
                "approval_id": approval.approval_id,
                "payment_id": approval.payment_id,
                "action": approval.action,
                "status": approval.status,
                "idempotency_key": approval.idempotency_key,
            }
            if approval
            else None
        ),
        "audit": {
            "audit_id": audit.audit_id,
            "idempotency_key": audit.idempotency_key,
            "status": audit.status,
        },
    }

@router.get("/audit/{payment_id}")
def recovery_audit(
    payment_id: str,
    db: Session = Depends(get_db),
):
    audits = (
        db.query(RecoveryAudit)
        .filter(
            RecoveryAudit.payment_id == payment_id
        )
        .order_by(
            RecoveryAudit.created_at.desc()
        )
        .all()
    )

    return [
        {
            "audit_id": audit.audit_id,
            "payment_id": audit.payment_id,
            "idempotency_key": audit.idempotency_key,
            "action": audit.action,
            "status": audit.status,
            "reason": audit.reason,
            "confidence": audit.confidence,
            "result": audit.result,
            "created_at": audit.created_at,
        }
        for audit in audits
    ]
