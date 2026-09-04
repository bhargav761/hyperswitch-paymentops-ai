import json
from typing import Any

from app.ai.contracts import AIRecommendation
from app.observability import metrics
from app.ai.guardrails import validate_recovery_recommendation


def build_ai_recommendation(
    *,
    llm_response: str,
    default_confidence: float = 0.0,
) -> dict[str, Any]:
    """Convert a constrained LLM response into a guarded advisory recommendation."""

    metrics.increment("ai_recommendations")

    try:
        payload = json.loads(llm_response)
    except (TypeError, json.JSONDecodeError):
        recommendation = AIRecommendation(
            action="unknown",
            confidence=default_confidence,
            reason="LLM response was not valid structured recommendation JSON.",
            reason_codes=("LLM_RESPONSE_INVALID",),
        )

        guardrail = validate_recovery_recommendation(
            action=recommendation.action,
            confidence=recommendation.confidence,
        )

        metrics.increment("ai_recommendation_invalid")
        metrics.increment("ai_guardrail_blocks")

        return {
            "recommendation": recommendation,
            "guardrail": guardrail,
        }

    action = str(payload.get("action", "unknown")).strip()
    confidence = float(payload.get("confidence", default_confidence))
    reason = str(
        payload.get(
            "reason",
            "No recommendation rationale was supplied.",
        )
    ).strip()

    raw_reason_codes = payload.get("reason_codes", [])
    if isinstance(raw_reason_codes, list):
        reason_codes = tuple(str(code) for code in raw_reason_codes)
    else:
        reason_codes = ("LLM_REASON_CODES_INVALID",)

    recommendation = AIRecommendation(
        action=action,
        confidence=max(0.0, min(1.0, confidence)),
        reason=reason,
        reason_codes=reason_codes,
    )

    guardrail = validate_recovery_recommendation(
        action=recommendation.action,
        confidence=recommendation.confidence,
    )

    if not guardrail["allowed"]:
        metrics.increment("ai_guardrail_blocks")

    return {
        "recommendation": recommendation,
        "guardrail": guardrail,
    }
