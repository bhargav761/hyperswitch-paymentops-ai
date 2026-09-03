BLOCKED_ACTIONS = {
    "capture",
    "refund",
    "void",
    "unknown",
}


def validate_recovery_recommendation(
    *,
    action: str,
    confidence: float,
) -> dict:
    normalized_action = action.upper().strip()

    if normalized_action.lower() in BLOCKED_ACTIONS:
        return {
            "allowed": False,
            "reason": "Action is outside the AI recovery safety boundary.",
        }

    if confidence < 0.50:
        return {
            "allowed": False,
            "reason": "AI confidence is below the minimum recovery threshold.",
        }

    return {
        "allowed": True,
        "reason": "Recommendation satisfies AI recovery guardrails.",
    }
