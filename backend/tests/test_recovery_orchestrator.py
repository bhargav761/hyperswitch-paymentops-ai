from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.recovery_orchestrator import orchestrate_recovery


def _payment():
    return SimpleNamespace(
        payment_id="pay_orchestrator_001",
        amount=100.0,
        currency="INR",
        method="card",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="temporary network failure",
        connector="stripe",
        latency_ms=450,
    )


def _policy(decision="DENY"):
    return SimpleNamespace(
        decision=decision,
        allowed=decision == "ALLOW",
        requires_approval=decision == "APPROVAL_REQUIRED",
        action="RETRY_NOW",
        idempotency_key="recovery:pay_orchestrator_001:RETRY_NOW",
        reason_codes=("TEST",),
    )


def _nba():
    return SimpleNamespace(
        action="RETRY_NOW",
        confidence=0.9,
        reason="Retry is appropriate.",
        requires_approval=False,
    )


@patch("app.services.recovery_orchestrator.create_recovery_audit")
@patch("app.services.recovery_orchestrator.analyze_payment_with_ai")
@patch("app.services.recovery_orchestrator.build_next_best_action")
@patch("app.services.recovery_orchestrator.prepare_recovery_action")
@patch("app.services.recovery_orchestrator.decide_recovery")
@patch("app.services.recovery_orchestrator.analyze_payment")
@patch("app.services.recovery_orchestrator.evaluate_policy_gate")
def test_orchestrator_blocks_policy_denial(
    policy_gate,
    incident_fn,
    decision_fn,
    prepare_fn,
    nba_fn,
    ai_fn,
    audit_fn,
):
    policy_gate.return_value = _policy("DENY")
    incident_fn.return_value = {
        "root_cause": "network",
        "risk_score": 0.2,
    }
    decision_fn.return_value = SimpleNamespace(
        action="RETRY_NOW",
        confidence=0.9,
        reason="retry",
        requires_approval=False,
    )
    prepare_fn.return_value = {}
    nba_fn.return_value = _nba()
    ai_fn.return_value = {"guardrail": {"allowed": True}}
    audit_fn.return_value = SimpleNamespace(audit_id="audit-1")

    result = orchestrate_recovery(
        db=Mock(),
        payment=_payment(),
        hyperswitch_base_url="http://localhost",
        hyperswitch_api_key=None,
        hyperswitch_timeout_seconds=1.0,
    )

    assert result.execution["status"] == "blocked"
    assert result.execution["executed"] is False


@patch("app.services.recovery_orchestrator.create_or_get_approval")
@patch("app.services.recovery_orchestrator.create_recovery_audit")
@patch("app.services.recovery_orchestrator.analyze_payment_with_ai")
@patch("app.services.recovery_orchestrator.build_next_best_action")
@patch("app.services.recovery_orchestrator.decide_recovery")
@patch("app.services.recovery_orchestrator.analyze_payment")
@patch("app.services.recovery_orchestrator.evaluate_policy_gate")
def test_orchestrator_requires_approval(
    policy_gate,
    incident_fn,
    decision_fn,
    nba_fn,
    ai_fn,
    audit_fn,
    approval_fn,
):
    policy_gate.return_value = _policy("APPROVAL_REQUIRED")
    incident_fn.return_value = {
        "root_cause": "network",
        "risk_score": 0.8,
    }
    decision_fn.return_value = SimpleNamespace(
        action="RETRY_NOW",
        confidence=0.8,
        reason="retry",
        requires_approval=True,
    )
    nba_fn.return_value = _nba()
    ai_fn.return_value = {"guardrail": {"allowed": True}}
    approval_fn.return_value = SimpleNamespace(approval_id="approval-1")
    audit_fn.return_value = SimpleNamespace(audit_id="audit-2")

    result = orchestrate_recovery(
        db=Mock(),
        payment=_payment(),
        hyperswitch_base_url="http://localhost",
        hyperswitch_api_key=None,
        hyperswitch_timeout_seconds=1.0,
    )

    assert result.execution["status"] == "approval_required"
    assert result.approval.approval_id == "approval-1"
    assert result.execution["executed"] is False
