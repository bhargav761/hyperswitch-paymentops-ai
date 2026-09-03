from app.ai.diagnosis import diagnose_payment
from app.ai.guardrails import validate_recovery_recommendation


def analyze_payment(
    *,
    status: str,
    failure_code: str | None = None,
    failure_reason: str | None = None,
    recommended_action: str,
) -> dict:
    diagnosis = diagnose_payment(
        status=status,
        failure_code=failure_code,
        failure_reason=failure_reason,
    )

    guardrail = validate_recovery_recommendation(
        action=recommended_action,
        confidence=diagnosis["confidence"],
    )

    return {
        "diagnosis": diagnosis,
        "recommendation": {
            "action": recommended_action,
            "confidence": diagnosis["confidence"],
        },
        "guardrail": guardrail,
    }
