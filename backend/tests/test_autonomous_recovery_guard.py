from app.services.autonomous_recovery_guard import (
    evaluate_autonomous_recovery,
)


def _eligible(**overrides):
    values = {
        "policy_decision": "ALLOW",
        "policy_allowed": True,
        "requires_approval": False,
        "ai_guardrail_allowed": True,
        "confidence": 0.90,
        "risk_score": 0.20,
        "action": "RETRY_NOW",
    }
    values.update(overrides)
    return evaluate_autonomous_recovery(**values)


def test_high_confidence_low_risk_retry_is_autonomous():
    decision = _eligible()

    assert decision.eligible is True
    assert decision.reason_codes == ("AUTONOMOUS_ELIGIBLE",)


def test_policy_denial_blocks_autonomous_execution():
    decision = _eligible(
        policy_decision="DENY",
        policy_allowed=False,
    )

    assert decision.eligible is False
    assert "POLICY_NOT_ALLOWED" in decision.reason_codes


def test_approval_requirement_blocks_autonomous_execution():
    decision = _eligible(requires_approval=True)

    assert decision.eligible is False
    assert "HUMAN_APPROVAL_REQUIRED" in decision.reason_codes


def test_ai_guardrail_block_blocks_autonomous_execution():
    decision = _eligible(ai_guardrail_allowed=False)

    assert decision.eligible is False
    assert "AI_GUARDRAIL_BLOCKED" in decision.reason_codes


def test_low_confidence_blocks_autonomous_execution():
    decision = _eligible(confidence=0.79)

    assert decision.eligible is False
    assert "CONFIDENCE_BELOW_AUTONOMOUS_THRESHOLD" in decision.reason_codes


def test_high_risk_blocks_autonomous_execution():
    decision = _eligible(risk_score=0.41)

    assert decision.eligible is False
    assert "RISK_ABOVE_AUTONOMOUS_THRESHOLD" in decision.reason_codes


def test_unsupported_action_blocks_autonomous_execution():
    decision = _eligible(action="REFUND")

    assert decision.eligible is False
    assert "ACTION_NOT_AUTONOMOUSLY_SUPPORTED" in decision.reason_codes


def test_multiple_safety_conditions_are_reported():
    decision = _eligible(
        policy_decision="DENY",
        policy_allowed=False,
        requires_approval=True,
        ai_guardrail_allowed=False,
        confidence=0.50,
        risk_score=0.90,
        action="REFUND",
    )

    assert decision.eligible is False
    assert len(decision.reason_codes) == 6
