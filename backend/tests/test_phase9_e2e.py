from types import SimpleNamespace

from app.services.closed_loop_verification import verify_recovery
from app.services.gitops_controller import build_argo_rollout, build_gitops_change
from app.services.incident_commander import analyze_system_incident
from app.services.remediation_planner import build_remediation_plan
from app.services.revenue_observability import (
    build_revenue_reliability_snapshot,
    snapshot_to_dict,
)


def _payment(payment_id, amount, status="failed"):
    return SimpleNamespace(
        payment_id=payment_id,
        amount=amount,
        currency="INR",
        method="upi",
        connector="connector_a",
        region="IN",
        status=status,
        failure_code="NETWORK_ERROR" if status == "failed" else None,
        failure_reason="connector degradation" if status == "failed" else None,
        latency_ms=3500 if status == "failed" else 800,
    )


def test_phase9_closed_loop_revenue_reliability():
    payments = [
        _payment("p1", 300000),
        _payment("p2", 300000),
        _payment("p3", 300000),
        _payment("p4", 300000),
        _payment("p5", 300000),
    ]

    incident = analyze_system_incident(payments)

    assert incident["incident"] is True
    assert incident["incident_id"].startswith("INC-")
    assert incident["revenue_at_risk_per_hour"] == 1_500_000.0

    revenue_decision = incident["revenue_decision"]

    assert revenue_decision["decision"] == "INTERVENE"
    assert revenue_decision["target_connector"] == "connector_b"
    assert revenue_decision["traffic_shift_percent"] == 35
    assert revenue_decision["expected_revenue_protected_per_hour"] > 0

    decision = SimpleNamespace(
        decision=revenue_decision["decision"],
        action=revenue_decision["action"],
        target_connector=revenue_decision["target_connector"],
        traffic_shift_percent=revenue_decision["traffic_shift_percent"],
        expected_revenue_protected_per_hour=(
            revenue_decision["expected_revenue_protected_per_hour"]
        ),
    )

    plan = build_remediation_plan(
        decision=decision,
        observation_window_seconds=300,
    )

    assert plan.status == "READY_FOR_POLICY_VALIDATION"

    change = build_gitops_change(
        plan=plan,
        confidence=revenue_decision["confidence"],
        intervention_risk=revenue_decision["intervention_risk"],
    )

    assert change.validation_status == "APPROVED"

    rollout = build_argo_rollout(
        change=change,
        observation_window_seconds=plan.observation_window_seconds,
    )

    assert rollout["status"] == "READY"
    assert rollout["verification_required"] is True

    verification = verify_recovery(
        failure_rate_before=0.50,
        failure_rate_after=0.05,
        latency_before_ms=3500,
        latency_after_ms=900,
        revenue_at_risk_before_per_hour=1_500_000,
        revenue_at_risk_after_per_hour=250_000,
        payments_recovered=42,
    )

    assert verification.status == "VERIFIED"
    assert verification.revenue_protected_per_hour == 1_250_000
    assert verification.revenue_recovered == 1_250_000

    snapshot = build_revenue_reliability_snapshot(
        correlation_id="phase9-e2e-001",
        incident=incident,
        plan=plan,
        change=change,
        verification=verification,
        timeline=(
            "INCIDENT_DETECTED",
            "REVENUE_DECISION",
            "REMEDIATION_PLANNED",
            "GITOPS_CHANGE",
            "ARGO_ROLLOUT",
            "VERIFIED",
        ),
    )

    payload = snapshot_to_dict(snapshot)

    assert payload["verification_status"] == "VERIFIED"
    assert payload["revenue_at_risk_per_hour"]["before"] == 1_500_000
    assert payload["revenue_at_risk_per_hour"]["after"] == 250_000
    assert payload["revenue_protected_per_hour"] == 1_250_000
    assert payload["revenue_recovered"] == 1_250_000
    assert payload["payments_recovered"] == 42
    assert payload["rollback_required"] is False
    assert len(payload["timeline"]) == 6
