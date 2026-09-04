from decimal import Decimal
from types import SimpleNamespace

from app.services.incident_commander import analyze_system_incident


def _payment(
    payment_id,
    *,
    status="failed",
    amount="10000",
    connector="connector_a",
    method="upi",
    region="IN",
    failure_code="NETWORK_ERROR",
    latency_ms=2500,
):
    return SimpleNamespace(
        payment_id=payment_id,
        amount=Decimal(amount),
        currency="INR",
        method=method,
        connector=connector,
        region=region,
        status=status,
        failure_code=failure_code,
        failure_reason="network degradation",
        latency_ms=latency_ms,
    )


def test_incident_commander_detects_systemic_incident():
    payments = [
        _payment("p1", amount="100000"),
        _payment("p2", amount="200000"),
        _payment("p3", amount="300000"),
        _payment("p4", amount="400000"),
        _payment("p5", amount="500000"),
    ]

    result = analyze_system_incident(payments)

    assert result["incident"] is True
    assert result["incident_id"].startswith("INC-")
    assert result["severity"] in {"high", "critical"}
    assert result["root_cause"] == "connector_or_network_degradation"
    assert result["affected_connector"] == "connector_a"
    assert result["affected_method"] == "upi"
    assert result["affected_region"] == "IN"
    assert result["affected_payments"] == 5
    assert result["revenue_at_risk_per_hour"] == 1500000.0
    assert "HIGH_FAILURE_RATE" in result["signals"]
    assert result["recommended_action"] == "evaluate_connector_reroute"


def test_incident_commander_does_not_raise_incident_for_healthy_payments():
    payments = [
        _payment(
            "p1",
            status="succeeded",
            failure_code=None,
            latency_ms=300,
        ),
        _payment(
            "p2",
            status="succeeded",
            failure_code=None,
            latency_ms=400,
        ),
    ]

    result = analyze_system_incident(payments)

    assert result["incident"] is False
    assert result["incident_id"] is None
    assert result["affected_payments"] == 0
    assert result["revenue_at_risk_per_hour"] == 0.0
    assert result["recommended_action"] == "continue_observation"


def test_incident_commander_handles_empty_telemetry():
    result = analyze_system_incident([])

    assert result["incident"] is False
    assert result["incident_id"] is None
    assert result["root_cause"] == "insufficient_payment_data"
    assert result["confidence"] == 0.0


def test_incident_commander_includes_revenue_aware_decision():
    payments = [
        _payment(
            f"p{i}",
            amount="300000",
            connector="connector_a",
            method="upi",
            region="IN",
            status="failed",
            failure_code="NETWORK_ERROR",
            latency_ms=3500,
        )
        for i in range(5)
    ]

    result = analyze_system_incident(payments)

    decision = result["revenue_decision"]

    assert decision["decision"] == "INTERVENE"
    assert decision["action"] == "SHIFT_TRAFFIC"
    assert decision["target_connector"] == "connector_b"
    assert decision["traffic_shift_percent"] == 35
    assert decision["expected_revenue_protected_per_hour"] > 0
    assert decision["rollback_required"] is True
