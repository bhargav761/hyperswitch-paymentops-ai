from dataclasses import dataclass


@dataclass(frozen=True)
class AutonomousRecoveryDecision:
    eligible: bool
    reason: str
    reason_codes: tuple[str, ...]


def evaluate_autonomous_recovery(
    *,
    policy_decision: str,
    policy_allowed: bool,
    requires_approval: bool,
    ai_guardrail_allowed: bool,
    confidence: float,
    risk_score: float,
    action: str,
) -> AutonomousRecoveryDecision:
    reasons: list[str] = []

    if policy_decision != "ALLOW" or not policy_allowed:
        reasons.append("POLICY_NOT_ALLOWED")

    if requires_approval:
        reasons.append("HUMAN_APPROVAL_REQUIRED")

    if not ai_guardrail_allowed:
        reasons.append("AI_GUARDRAIL_BLOCKED")

    if confidence < 0.80:
        reasons.append("CONFIDENCE_BELOW_AUTONOMOUS_THRESHOLD")

    if risk_score > 0.40:
        reasons.append("RISK_ABOVE_AUTONOMOUS_THRESHOLD")

    if action not in {"RETRY_NOW", "RECONCILE"}:
        reasons.append("ACTION_NOT_AUTONOMOUSLY_SUPPORTED")

    if reasons:
        return AutonomousRecoveryDecision(
            eligible=False,
            reason="Recovery requires controlled human or policy intervention.",
            reason_codes=tuple(reasons),
        )

    return AutonomousRecoveryDecision(
        eligible=True,
        reason="Recovery satisfies deterministic autonomous execution criteria.",
        reason_codes=("AUTONOMOUS_ELIGIBLE",),
    )
