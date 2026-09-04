from decimal import Decimal

from app.ai.context_orchestrator import build_ai_context
from app.models.payment import Payment


def test_build_ai_context_combines_evidence_and_rag():
    payment = Payment(
        payment_id="pay_ctx_001",
        amount=Decimal("1250.00"),
        currency="INR",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="temporary network failure",
        connector="hyperswitch",
        latency_ms=420.0,
    )

    incident = {
        "incident": True,
        "severity": "high",
        "risk_score": 0.72,
        "revenue_at_risk": 1250.0,
        "recovery_priority": "high",
        "root_cause": "network_error",
        "signals": ["latency_spike"],
        "recommended_action": "retry",
    }

    context = build_ai_context(
        payment=payment,
        incident=incident,
    )

    assert context["payment"]["payment_id"] == "pay_ctx_001"
    assert context["incident"]["severity"] == "high"
    assert context["recovery_guidance"]
    assert context["recovery_guidance"][0]["title"]


def test_build_ai_context_respects_guidance_limit():
    payment = Payment(
        payment_id="pay_ctx_002",
        amount=Decimal("500.00"),
        currency="INR",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="network failure",
        connector="hyperswitch",
        latency_ms=100.0,
    )

    context = build_ai_context(
        payment=payment,
        incident={},
        guidance_limit=1,
    )

    assert len(context["recovery_guidance"]) <= 1
