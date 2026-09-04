from dataclasses import dataclass

from app.ai.agent import analyze_payment as analyze_payment_with_ai
from app.recovery.actions import prepare_recovery_action
from app.recovery.decision_engine import decide_recovery
from app.recovery.next_best_action import build_next_best_action
from app.recovery.policy_gateway import evaluate_policy_gate
from app.services.approval_service import create_or_get_approval
from app.services.audit_service import create_recovery_audit
from app.services.incident_service import analyze_payment
from app.services.recovery_execution_service import (
    build_hyperswitch_adapter,
    execute_policy_approved_recovery,
)
from app.routing.health_score import calculate_connector_health
from app.routing.route_decision import decide_route


@dataclass(frozen=True)
class RecoveryOrchestrationResult:
    incident: dict
    decision: object
    next_best_action: object
    policy: object
    ai_analysis: dict
    route: dict
    execution: dict
    approval: object | None
    audit: object


def orchestrate_recovery(
    *,
    db,
    payment,
    hyperswitch_base_url: str,
    hyperswitch_api_key: str | None,
    hyperswitch_timeout_seconds: float,
) -> RecoveryOrchestrationResult:
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

    if policy.decision == "DENY":
        execution = {
            "executed": False,
            "status": "blocked",
            "action": policy.action,
            "message": "Recovery action blocked by the policy gateway.",
            "idempotency_key": policy.idempotency_key,
        }
    elif policy.decision == "APPROVAL_REQUIRED":
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
            base_url=hyperswitch_base_url,
            api_key=hyperswitch_api_key,
            timeout_seconds=hyperswitch_timeout_seconds,
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
            "route": route,
            "ai": {
                "diagnosis": ai_analysis.get("diagnosis"),
                "recovery_prediction": ai_analysis.get("recovery_prediction"),
                "recommendation": ai_analysis.get("recommendation"),
                "routing": ai_analysis.get("routing"),
                "evidence": ai_analysis.get("evidence"),
            },
        },
    )

    return RecoveryOrchestrationResult(
        incident=incident,
        decision=decision,
        next_best_action=next_best_action,
        policy=policy,
        ai_analysis=ai_analysis,
        route=route,
        execution=execution,
        approval=approval,
        audit=audit,
    )
