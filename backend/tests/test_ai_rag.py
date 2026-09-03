from app.ai.agent import analyze_payment
from app.ai.diagnosis import diagnose_payment
from app.rag.retriever import retrieve_recovery_guidance


def test_rag_retrieves_network_guidance():
    results = retrieve_recovery_guidance(
        status="failed",
        failure_code="network_timeout",
    )

    assert results
    assert results[0]["id"] == "network_failure"


def test_diagnosis_uses_retrieved_evidence():
    result = diagnose_payment(
        status="failed",
        failure_code="issuer_decline",
    )

    assert result["root_cause"] == "issuer_decline"
    assert result["confidence"] == 0.90
    assert result["evidence"]


def test_ai_agent_applies_guardrails():
    result = analyze_payment(
        status="failed",
        failure_code="network_timeout",
        recommended_action="RETRY_NOW",
    )

    assert result["recommendation"]["action"] == "RETRY_NOW"
    assert result["guardrail"]["allowed"] is True


def test_ai_agent_blocks_unsafe_action():
    result = analyze_payment(
        status="failed",
        failure_code="network_timeout",
        recommended_action="REFUND",
    )

    assert result["guardrail"]["allowed"] is False
