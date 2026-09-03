from app.ai.contracts import (
    AIDiagnosis,
    AIAnalysis,
    AIRecoveryPrediction,
    AIRecommendation,
    AIRoutingRecommendation,
)
from app.ai.diagnosis import diagnose_payment
from app.ai.evidence import build_payment_evidence
from app.ai.guardrails import validate_recovery_recommendation
from app.observability import metrics


def _estimate_recovery_probability(
    *,
    status: str,
    diagnosis_confidence: float,
    recommended_action: str,
) -> tuple[float, float, str]:
    """Estimate recovery probability using bounded deterministic signals.

    This is the Phase 5 intelligence baseline. It is deliberately provider
    independent so a trained model or LLM can replace it later without
    changing the payment-control boundary.
    """

    normalized_status = status.lower().strip()
    normalized_action = recommended_action.upper().strip()

    probability = diagnosis_confidence
    rationale = "Recovery estimate is based on diagnosis confidence."

    if normalized_status == "failed":
        if normalized_action in {"RETRY_NOW", "RETRY_LATER"}:
            probability = min(0.95, diagnosis_confidence + 0.02)
            rationale = (
                "Transient recovery action is supported by the diagnosed "
                "failure condition."
            )
        elif normalized_action == "ALTERNATIVE_PAYMENT":
            probability = min(0.92, diagnosis_confidence)
            rationale = (
                "Alternative payment is preferred for the diagnosed "
                "non-retryable failure."
            )
        elif normalized_action == "HUMAN_REVIEW":
            probability = min(0.60, diagnosis_confidence)
            rationale = (
                "Automatic recovery is uncertain and requires human review."
            )

    elif normalized_status == "pending":
        probability = min(0.90, diagnosis_confidence)
        rationale = (
            "Pending payments require state verification before recovery."
        )

    probability = round(max(0.0, min(1.0, probability)), 2)

    return probability, diagnosis_confidence, rationale


def _build_routing_recommendation(
    *,
    payment=None,
    incident: dict | None = None,
) -> AIRoutingRecommendation:
    """Build an advisory routing recommendation from normalized evidence."""

    if payment is None:
        return AIRoutingRecommendation(
            connector=None,
            confidence=0.0,
            reason="Routing recommendation requires payment evidence.",
            reason_codes=("ROUTING_EVIDENCE_MISSING",),
        )

    connector = getattr(payment, "connector", None)

    if incident:
        signals = set(incident.get("signals", []))
        if "NETWORK_ERROR" in signals or "TIMEOUT" in signals:
            return AIRoutingRecommendation(
                connector=connector,
                confidence=0.90 if connector else 0.0,
                reason=(
                    "Current connector is retained as the advisory route; "
                    "deterministic routing must evaluate connector health "
                    "before any reroute."
                ),
                reason_codes=(
                    "PAYMENT_FAILURE_SIGNAL",
                    "CONNECTOR_HEALTH_REQUIRED",
                ),
            )

    return AIRoutingRecommendation(
        connector=connector,
        confidence=0.85 if connector else 0.0,
        reason=(
            "Current connector is the initial advisory route; "
            "deterministic routing remains authoritative."
        ),
        reason_codes=("CURRENT_CONNECTOR",),
    )


def analyze_payment(
    *,
    status: str,
    failure_code: str | None = None,
    failure_reason: str | None = None,
    recommended_action: str,
    payment=None,
    incident: dict | None = None,
) -> dict:
    metrics.increment("ai_analyses")
    diagnosis = diagnose_payment(
        status=status,
        failure_code=failure_code,
        failure_reason=failure_reason,
    )

    evidence_payload = None
    if payment is not None and incident is not None:
        evidence_payload = build_payment_evidence(
            payment=payment,
            incident=incident,
        )

    # AI remains advisory: derive an evidence-aware recommendation while
    # preserving the deterministic recovery/policy layers as authority.
    evidence_action = recommended_action
    evidence_reason_codes = tuple(
        evidence["id"]
        for evidence in diagnosis["evidence"]
        if "id" in evidence
    )

    if evidence_payload is not None:
        incident_action = evidence_payload["incident"].get("recommended_action")
        if incident_action:
            evidence_action = str(incident_action)

    if evidence_action != recommended_action:
        recommendation_reason = (
            "AI evidence indicates a different recovery path; "
            "deterministic policy remains authoritative."
        )
    else:
        recommendation_reason = (
            "AI recommendation is consistent with the available "
            "payment and incident evidence."
        )

    guardrail = validate_recovery_recommendation(
        action=evidence_action,
        confidence=diagnosis["confidence"],
    )
    if not guardrail["allowed"]:
        metrics.increment("ai_guardrail_blocks")

    probability, prediction_confidence, rationale = (
        _estimate_recovery_probability(
            status=status,
            diagnosis_confidence=diagnosis["confidence"],
            recommended_action=recommended_action,
        )
    )

    routing_recommendation = _build_routing_recommendation(
        payment=payment,
        incident=incident,
    )

    structured_analysis = AIAnalysis(
        diagnosis=AIDiagnosis(
            root_cause=diagnosis["root_cause"],
            confidence=diagnosis["confidence"],
            evidence=tuple(diagnosis["evidence"]),
        ),
        recovery_prediction=AIRecoveryPrediction(
            probability=probability,
            confidence=prediction_confidence,
            rationale=rationale,
        ),
        recommendation=AIRecommendation(
            action=evidence_action,
            confidence=diagnosis["confidence"],
            reason=recommendation_reason,
            reason_codes=evidence_reason_codes,
        ),
        routing=routing_recommendation,
    )

    return {
        "diagnosis": diagnosis,
        "recommendation": {
            "action": evidence_action,
            "confidence": diagnosis["confidence"],
        },
        "guardrail": guardrail,
        "recovery_prediction": {
            "probability": structured_analysis.recovery_prediction.probability,
            "confidence": structured_analysis.recovery_prediction.confidence,
            "rationale": structured_analysis.recovery_prediction.rationale,
        },
        "analysis": structured_analysis,
        "evidence": evidence_payload,
        "routing": {
            "connector": routing_recommendation.connector,
            "confidence": routing_recommendation.confidence,
            "reason": routing_recommendation.reason,
            "reason_codes": list(routing_recommendation.reason_codes),
        },
    }
