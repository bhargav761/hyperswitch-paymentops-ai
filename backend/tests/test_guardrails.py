
def test_guardrail_blocks_capture():
    from app.ai.guardrails import validate_recovery_recommendation

    result = validate_recovery_recommendation(
        action="capture",
        confidence=0.95,
    )

    assert result["allowed"] is False


def test_guardrail_blocks_low_confidence():
    from app.ai.guardrails import validate_recovery_recommendation

    result = validate_recovery_recommendation(
        action="RETRY_NOW",
        confidence=0.49,
    )

    assert result["allowed"] is False


def test_guardrail_allows_valid_retry():
    from app.ai.guardrails import validate_recovery_recommendation

    result = validate_recovery_recommendation(
        action="RETRY_NOW",
        confidence=0.90,
    )

    assert result["allowed"] is True
