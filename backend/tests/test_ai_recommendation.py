import json

from app.ai.recommendation import build_ai_recommendation


def test_valid_llm_recommendation_is_guarded():
    result = build_ai_recommendation(
        llm_response=json.dumps(
            {
                "action": "RETRY_LATER",
                "confidence": 0.82,
                "reason": "Transient network failure supports retry with backoff.",
                "reason_codes": ["NETWORK_FAILURE", "TRANSIENT"],
            }
        )
    )

    recommendation = result["recommendation"]

    assert recommendation.action == "RETRY_LATER"
    assert recommendation.confidence == 0.82
    assert recommendation.reason_codes == (
        "NETWORK_FAILURE",
        "TRANSIENT",
    )
    assert result["guardrail"]["allowed"] is True


def test_blocked_llm_action_is_rejected():
    result = build_ai_recommendation(
        llm_response=json.dumps(
            {
                "action": "REFUND",
                "confidence": 0.99,
                "reason": "Refund the payment.",
                "reason_codes": ["REFUND"],
            }
        )
    )

    assert result["guardrail"]["allowed"] is False


def test_low_confidence_llm_recommendation_is_rejected():
    result = build_ai_recommendation(
        llm_response=json.dumps(
            {
                "action": "RETRY_LATER",
                "confidence": 0.20,
                "reason": "Insufficient confidence.",
                "reason_codes": ["LOW_CONFIDENCE"],
            }
        )
    )

    assert result["guardrail"]["allowed"] is False


def test_invalid_llm_response_becomes_unknown_and_is_blocked():
    result = build_ai_recommendation(
        llm_response="retry this payment immediately",
        default_confidence=0.90,
    )

    recommendation = result["recommendation"]

    assert recommendation.action == "unknown"
    assert recommendation.reason_codes == ("LLM_RESPONSE_INVALID",)
    assert result["guardrail"]["allowed"] is False
