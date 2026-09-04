from app.ai.safety_boundary import evaluate_ai_recommendation_safety


def _recommendation(
    action="RETRY_NOW",
    confidence=0.90,
    allowed=True,
):
    return {
        "action": action,
        "confidence": confidence,
        "guardrail": {
            "allowed": allowed,
        },
    }


def test_safe_ai_recommendation_can_be_autonomous_when_policy_allows():
    decision = evaluate_ai_recommendation_safety(
        recommendation=_recommendation(),
        policy_decision="ALLOW",
        policy_allowed=True,
        requires_approval=False,
        risk_score=0.20,
    )

    assert decision.eligible is True
    assert decision.reason_codes == ("AUTONOMOUS_ELIGIBLE",)


def test_ai_recommendation_cannot_bypass_required_approval():
    decision = evaluate_ai_recommendation_safety(
        recommendation=_recommendation(),
        policy_decision="ALLOW",
        policy_allowed=True,
        requires_approval=True,
        risk_score=0.20,
    )

    assert decision.eligible is False
    assert "HUMAN_APPROVAL_REQUIRED" in decision.reason_codes


def test_ai_guardrail_block_prevents_autonomous_execution():
    decision = evaluate_ai_recommendation_safety(
        recommendation=_recommendation(allowed=False),
        policy_decision="ALLOW",
        policy_allowed=True,
        requires_approval=False,
        risk_score=0.20,
    )

    assert decision.eligible is False
    assert "AI_GUARDRAIL_BLOCKED" in decision.reason_codes


def test_ai_cannot_override_policy_denial():
    decision = evaluate_ai_recommendation_safety(
        recommendation=_recommendation(),
        policy_decision="DENY",
        policy_allowed=False,
        requires_approval=False,
        risk_score=0.10,
    )

    assert decision.eligible is False
    assert "POLICY_NOT_ALLOWED" in decision.reason_codes


def test_high_risk_ai_recommendation_is_not_autonomous():
    decision = evaluate_ai_recommendation_safety(
        recommendation=_recommendation(),
        policy_decision="ALLOW",
        policy_allowed=True,
        requires_approval=False,
        risk_score=0.80,
    )

    assert decision.eligible is False
    assert "RISK_ABOVE_AUTONOMOUS_THRESHOLD" in decision.reason_codes
