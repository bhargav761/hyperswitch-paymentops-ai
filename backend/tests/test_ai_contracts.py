from app.ai.contracts import (
    AIDiagnosis,
    AIRecommendation,
    AIRecoveryPrediction,
)


def test_ai_diagnosis_contract():
    result = AIDiagnosis(
        root_cause="payment_timeout",
        confidence=0.90,
        evidence=(
            {
                "id": "network_failure",
                "score": 2,
            },
        ),
    )

    assert result.root_cause == "payment_timeout"
    assert result.confidence == 0.90
    assert len(result.evidence) == 1


def test_ai_recommendation_contract():
    result = AIRecommendation(
        action="RETRY_LATER",
        confidence=0.88,
        reason="Controlled retry is appropriate.",
        reason_codes=("PAYMENT_TIMEOUT", "CONTROLLED_RETRY"),
    )

    assert result.action == "RETRY_LATER"
    assert result.confidence == 0.88
    assert "PAYMENT_TIMEOUT" in result.reason_codes


def test_ai_recovery_prediction_contract():
    result = AIRecoveryPrediction(
        probability=0.84,
        confidence=0.91,
        rationale="Transient failure with strong recovery evidence.",
    )

    assert result.probability == 0.84
    assert result.confidence == 0.91


def test_ai_analysis_contains_structured_components():
    from app.ai.agent import analyze_payment

    result = analyze_payment(
        status="failed",
        failure_code="network_timeout",
        recommended_action="RETRY_NOW",
    )

    analysis = result["analysis"]

    assert analysis.diagnosis.root_cause == "network_timeout"
    assert analysis.diagnosis.confidence == 0.90
    assert analysis.recovery_prediction.probability == 0.92
    assert analysis.recommendation.action == "RETRY_NOW"


def test_ai_analysis_preserves_existing_phase_four_response():
    from app.ai.agent import analyze_payment

    result = analyze_payment(
        status="failed",
        failure_code="network_timeout",
        recommended_action="RETRY_NOW",
    )

    assert result["recommendation"]["action"] == "RETRY_NOW"
    assert result["recommendation"]["confidence"] == 0.90
    assert result["guardrail"]["allowed"] is True


def test_ai_recommendation_uses_incident_evidence_when_available():
    from types import SimpleNamespace

    from app.ai.agent import analyze_payment

    payment = SimpleNamespace(
        payment_id="pay_test",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="connector timeout",
        amount=1000,
        currency="INR",
        connector="stripe",
        latency_ms=800,
    )

    incident = {
        "incident": True,
        "severity": "high",
        "risk_score": 0.4,
        "revenue_at_risk": 1000,
        "recovery_priority": "high",
        "root_cause": "payment_network_degradation",
        "signals": ["NETWORK_ERROR"],
        "recommended_action": "reroute_or_retry",
    }

    result = analyze_payment(
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="connector timeout",
        recommended_action="HUMAN_REVIEW",
        payment=payment,
        incident=incident,
    )

    assert result["recommendation"]["action"] == "reroute_or_retry"
    assert result["analysis"].recommendation.action == "reroute_or_retry"
    assert result["evidence"]["payment"]["payment_id"] == "pay_test"
    assert result["evidence"]["incident"]["recommended_action"] == "reroute_or_retry"
    assert (
        result["analysis"].recommendation.reason
        == "AI evidence indicates a different recovery path; deterministic policy remains authoritative."
    )


def test_ai_routing_recommendation_is_advisory():
    from types import SimpleNamespace

    from app.ai.agent import analyze_payment

    payment = SimpleNamespace(
        payment_id="pay_route",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="connector timeout",
        amount=1000,
        currency="INR",
        connector="stripe",
        latency_ms=800,
    )

    incident = {
        "incident": True,
        "signals": ["NETWORK_ERROR"],
        "recommended_action": "reroute_or_retry",
    }

    result = analyze_payment(
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="connector timeout",
        recommended_action="reroute_or_retry",
        payment=payment,
        incident=incident,
    )

    assert result["routing"]["connector"] == "stripe"
    assert result["routing"]["confidence"] == 0.90
    assert "CONNECTOR_HEALTH_REQUIRED" in result["routing"]["reason_codes"]
    assert result["analysis"].routing.connector == "stripe"
