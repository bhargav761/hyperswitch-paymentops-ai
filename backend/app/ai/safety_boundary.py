from typing import Any

from app.observability import metrics
from app.services.autonomous_recovery_guard import (
    AutonomousRecoveryDecision,
    evaluate_autonomous_recovery,
)


def evaluate_ai_recommendation_safety(
    *,
    recommendation: dict[str, Any],
    policy_decision: str,
    policy_allowed: bool,
    requires_approval: bool,
    risk_score: float,
) -> AutonomousRecoveryDecision:
    """Apply the existing deterministic recovery boundary to an AI recommendation."""

    action = str(recommendation.get("action", "unknown"))
    confidence = float(recommendation.get("confidence", 0.0))

    guardrail = recommendation.get("guardrail", {})
    ai_guardrail_allowed = bool(guardrail.get("allowed", False))

    decision = evaluate_autonomous_recovery(
        policy_decision=policy_decision,
        policy_allowed=policy_allowed,
        requires_approval=requires_approval,
        ai_guardrail_allowed=ai_guardrail_allowed,
        confidence=confidence,
        risk_score=risk_score,
        action=action,
    )

    if decision.eligible:
        metrics.increment("ai_autonomous_eligible")
    elif "HUMAN_APPROVAL_REQUIRED" in decision.reason_codes:
        metrics.increment("ai_human_approval_required")

    return decision
