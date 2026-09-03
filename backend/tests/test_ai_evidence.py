from types import SimpleNamespace

from app.ai.evidence import build_payment_evidence


def test_build_payment_evidence_normalizes_payment_and_incident():
    payment = SimpleNamespace(
        payment_id="pay_123",
        status="failed",
        failure_code="network_timeout",
        failure_reason="Gateway timed out",
        amount=500,
        currency="INR",
        connector="hyperswitch",
        latency_ms=1200,
    )

    incident = {
        "incident": True,
        "severity": "high",
        "risk_score": 0.30,
        "revenue_at_risk": 500.0,
        "recovery_priority": "high",
        "root_cause": "payment_timeout",
        "signals": ["NETWORK_TIMEOUT"],
        "recommended_action": "retry_with_backoff",
    }

    result = build_payment_evidence(
        payment=payment,
        incident=incident,
    )

    assert result["payment"]["payment_id"] == "pay_123"
    assert result["payment"]["amount"] == 500.0
    assert result["payment"]["latency_ms"] == 1200.0

    assert result["incident"]["root_cause"] == "payment_timeout"
    assert result["incident"]["risk_score"] == 0.30
    assert result["incident"]["signals"] == ["NETWORK_TIMEOUT"]


def test_build_payment_evidence_handles_missing_optional_incident_fields():
    payment = SimpleNamespace(
        payment_id="pay_456",
        status="pending",
        failure_code=None,
        failure_reason=None,
        amount=100,
        currency="INR",
        connector=None,
        latency_ms=None,
    )

    result = build_payment_evidence(
        payment=payment,
        incident={},
    )

    assert result["payment"]["connector"] is None
    assert result["payment"]["latency_ms"] == 0.0
    assert result["incident"]["risk_score"] == 0.0
    assert result["incident"]["signals"] == []
