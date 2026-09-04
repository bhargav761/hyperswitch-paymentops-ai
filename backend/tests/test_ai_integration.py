import json
from decimal import Decimal

from app.ai.context_orchestrator import build_ai_context
from app.ai.rag_grounding import build_grounded_prompt
from app.ai.recommendation import build_ai_recommendation
from app.ai.safety_boundary import evaluate_ai_recommendation_safety
from app.models.payment import Payment
from app.services.incident_service import analyze_payment


def _payment() -> Payment:
    return Payment(
        payment_id="integration-ai-001",
        event_id="event-integration-ai-001",
        amount=Decimal("300000.00"),
        currency="INR",
        method="upi",
        connector="connector_a",
        region="IN",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="temporary connector network degradation",
        latency_ms=3500,
    )


def test_complete_ai_advisory_chain():
    payment = _payment()

    incident = analyze_payment(payment)

    context = build_ai_context(
        payment=payment,
        incident=incident,
    )

    prompt = build_grounded_prompt(
        user_prompt="What recovery action should be recommended?",
        context=context,
    )

    assert "PaymentOps recovery guidance" in prompt
    assert context["payment"]["payment_id"] == payment.payment_id
    assert context["recovery_guidance"]

    # Deterministic fake LLM response; no external provider call.
    llm_response = json.dumps(
        {
            "action": "RETRY_NOW",
            "confidence": 0.90,
            "reason": "Network degradation appears transient and grounded guidance supports retry.",
            "reason_codes": [
                "NETWORK_FAILURE",
                "TRANSIENT_FAILURE",
            ],
        }
    )

    recommendation_result = build_ai_recommendation(
        llm_response=llm_response,
    )

    recommendation = recommendation_result["recommendation"]

    assert recommendation.action == "RETRY_NOW"
    assert recommendation.confidence == 0.90
    assert recommendation_result["guardrail"]["allowed"] is True

    safety = evaluate_ai_recommendation_safety(
        recommendation={
            "action": recommendation.action,
            "confidence": recommendation.confidence,
            "guardrail": recommendation_result["guardrail"],
        },
        policy_decision="ALLOW",
        policy_allowed=True,
        requires_approval=False,
        risk_score=0.20,
    )

    assert safety.eligible is True
    assert safety.reason_codes == ("AUTONOMOUS_ELIGIBLE",)


def test_ai_chain_stops_when_guardrail_blocks_llm_action():
    payment = _payment()

    incident = analyze_payment(payment)
    context = build_ai_context(
        payment=payment,
        incident=incident,
    )

    prompt = build_grounded_prompt(
        user_prompt="Recommend the next action.",
        context=context,
    )

    assert prompt

    llm_response = json.dumps(
        {
            "action": "REFUND",
            "confidence": 0.99,
            "reason": "Unsafe action supplied by the model.",
            "reason_codes": ["UNSAFE_ACTION"],
        }
    )

    recommendation_result = build_ai_recommendation(
        llm_response=llm_response,
    )

    recommendation = recommendation_result["recommendation"]

    assert recommendation_result["guardrail"]["allowed"] is False

    safety = evaluate_ai_recommendation_safety(
        recommendation={
            "action": recommendation.action,
            "confidence": recommendation.confidence,
            "guardrail": recommendation_result["guardrail"],
        },
        policy_decision="ALLOW",
        policy_allowed=True,
        requires_approval=False,
        risk_score=0.20,
    )

    assert safety.eligible is False
    assert "AI_GUARDRAIL_BLOCKED" in safety.reason_codes
