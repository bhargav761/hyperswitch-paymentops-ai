from app.rag.retriever import retrieve_recovery_guidance


def diagnose_payment(
    *,
    status: str,
    failure_code: str | None = None,
    failure_reason: str | None = None,
) -> dict:
    guidance = retrieve_recovery_guidance(
        status=status,
        failure_code=failure_code,
        failure_reason=failure_reason,
    )

    if failure_code:
        root_cause = failure_code.lower()
    elif failure_reason:
        root_cause = failure_reason.lower()
    else:
        root_cause = status.lower()

    return {
        "root_cause": root_cause,
        "confidence": 0.90 if guidance else 0.60,
        "evidence": guidance,
    }
