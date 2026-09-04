from types import SimpleNamespace

from app.services.revenue_observability import (
    build_revenue_reliability_snapshot,
    snapshot_to_dict,
)


def test_revenue_observability_correlates_full_lifecycle():
    incident = {
        "incident_id": "INC-ABC12345",
        "failure_rate": 0.50,
        "average_latency_ms": 3500,
        "revenue_at_risk_per_hour": 1_500_000,
    }

    plan = SimpleNamespace(plan_id="PLAN-12345678")
    change = SimpleNamespace(change_id="CHANGE-12345678")

    verification = SimpleNamespace(
        status="VERIFIED",
        failure_rate_before=0.50,
        failure_rate_after=0.05,
        latency_before_ms=3500,
        latency_after_ms=900,
        revenue_at_risk_before_per_hour=1_500_000,
        revenue_at_risk_after_per_hour=250_000,
        revenue_protected_per_hour=1_250_000,
        revenue_recovered=1_250_000,
        payments_recovered=42,
        rollback_required=False,
    )

    snapshot = build_revenue_reliability_snapshot(
        correlation_id="corr-001",
        incident=incident,
        plan=plan,
        change=change,
        verification=verification,
        timeline=(
            "INCIDENT_DETECTED",
            "REVENUE_DECISION",
            "REMEDIATION_PLANNED",
            "GITOPS_CHANGE",
            "ROLLOUT",
            "VERIFIED",
        ),
    )

    assert snapshot.correlation_id == "corr-001"
    assert snapshot.incident_id == "INC-ABC12345"
    assert snapshot.plan_id == "PLAN-12345678"
    assert snapshot.change_id == "CHANGE-12345678"
    assert snapshot.verification_status == "VERIFIED"
    assert snapshot.revenue_protected_per_hour == 1_250_000
    assert snapshot.revenue_recovered == 1_250_000
    assert snapshot.payments_recovered == 42
    assert snapshot.rollback_required is False
    assert len(snapshot.timeline) == 6


def test_revenue_observability_serializes_operational_snapshot():
    incident = {
        "incident_id": "INC-001",
        "failure_rate": 0.30,
        "average_latency_ms": 2800,
        "revenue_at_risk_per_hour": 800_000,
    }

    snapshot = build_revenue_reliability_snapshot(
        correlation_id="corr-002",
        incident=incident,
    )

    payload = snapshot_to_dict(snapshot)

    assert payload["correlation_id"] == "corr-002"
    assert payload["incident_id"] == "INC-001"
    assert payload["verification_status"] == "PENDING"
    assert payload["failure_rate"]["before"] == 0.30
    assert payload["latency_ms"]["before"] == 2800
    assert payload["revenue_at_risk_per_hour"]["before"] == 800_000
    assert payload["revenue_protected_per_hour"] == 0.0
    assert payload["rollback_required"] is False


def test_failed_verification_is_visible_in_snapshot():
    incident = {
        "incident_id": "INC-ROLLBACK",
        "failure_rate": 0.50,
        "average_latency_ms": 3500,
        "revenue_at_risk_per_hour": 1_500_000,
    }

    verification = SimpleNamespace(
        status="ROLLBACK_REQUIRED",
        failure_rate_before=0.50,
        failure_rate_after=0.35,
        latency_before_ms=3500,
        latency_after_ms=3200,
        revenue_at_risk_before_per_hour=1_500_000,
        revenue_at_risk_after_per_hour=1_800_000,
        revenue_protected_per_hour=0.0,
        revenue_recovered=0.0,
        payments_recovered=0,
        rollback_required=True,
    )

    snapshot = build_revenue_reliability_snapshot(
        correlation_id="corr-003",
        incident=incident,
        verification=verification,
        timeline=("INCIDENT_DETECTED", "ROLLOUT", "ROLLBACK_REQUIRED"),
    )

    assert snapshot.verification_status == "ROLLBACK_REQUIRED"
    assert snapshot.rollback_required is True
    assert snapshot.revenue_protected_per_hour == 0.0
    assert "ROLLBACK_REQUIRED" in snapshot.timeline
