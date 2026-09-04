from dataclasses import dataclass


@dataclass(frozen=True)
class RevenueReliabilitySnapshot:
    correlation_id: str
    incident_id: str | None
    plan_id: str | None
    change_id: str | None
    verification_status: str
    failure_rate_before: float
    failure_rate_after: float
    latency_before_ms: float
    latency_after_ms: float
    revenue_at_risk_per_hour_before: float
    revenue_at_risk_per_hour_after: float
    revenue_protected_per_hour: float
    revenue_recovered: float
    payments_recovered: int
    rollback_required: bool
    timeline: tuple[str, ...]


def build_revenue_reliability_snapshot(
    *,
    correlation_id: str,
    incident: dict,
    plan=None,
    change=None,
    verification=None,
    timeline: list[str] | tuple[str, ...] = (),
) -> RevenueReliabilitySnapshot:
    verification_status = (
        verification.status
        if verification is not None
        else "PENDING"
    )

    return RevenueReliabilitySnapshot(
        correlation_id=correlation_id,
        incident_id=incident.get("incident_id"),
        plan_id=getattr(plan, "plan_id", None),
        change_id=getattr(change, "change_id", None),
        verification_status=verification_status,
        failure_rate_before=(
            float(verification.failure_rate_before)
            if verification is not None
            else float(incident.get("failure_rate", 0.0))
        ),
        failure_rate_after=(
            float(verification.failure_rate_after)
            if verification is not None
            else float(incident.get("failure_rate", 0.0))
        ),
        latency_before_ms=(
            float(verification.latency_before_ms)
            if verification is not None
            else float(incident.get("average_latency_ms", 0.0))
        ),
        latency_after_ms=(
            float(verification.latency_after_ms)
            if verification is not None
            else float(incident.get("average_latency_ms", 0.0))
        ),
        revenue_at_risk_per_hour_before=(
            float(verification.revenue_at_risk_before_per_hour)
            if verification is not None
            else float(incident.get("revenue_at_risk_per_hour", 0.0))
        ),
        revenue_at_risk_per_hour_after=(
            float(verification.revenue_at_risk_after_per_hour)
            if verification is not None
            else float(incident.get("revenue_at_risk_per_hour", 0.0))
        ),
        revenue_protected_per_hour=(
            float(verification.revenue_protected_per_hour)
            if verification is not None
            else 0.0
        ),
        revenue_recovered=(
            float(verification.revenue_recovered)
            if verification is not None
            else 0.0
        ),
        payments_recovered=(
            int(verification.payments_recovered)
            if verification is not None
            else 0
        ),
        rollback_required=(
            bool(verification.rollback_required)
            if verification is not None
            else False
        ),
        timeline=tuple(timeline),
    )


def snapshot_to_dict(
    snapshot: RevenueReliabilitySnapshot,
) -> dict:
    return {
        "correlation_id": snapshot.correlation_id,
        "incident_id": snapshot.incident_id,
        "plan_id": snapshot.plan_id,
        "change_id": snapshot.change_id,
        "verification_status": snapshot.verification_status,
        "failure_rate": {
            "before": snapshot.failure_rate_before,
            "after": snapshot.failure_rate_after,
        },
        "latency_ms": {
            "before": snapshot.latency_before_ms,
            "after": snapshot.latency_after_ms,
        },
        "revenue_at_risk_per_hour": {
            "before": snapshot.revenue_at_risk_per_hour_before,
            "after": snapshot.revenue_at_risk_per_hour_after,
        },
        "revenue_protected_per_hour": snapshot.revenue_protected_per_hour,
        "revenue_recovered": snapshot.revenue_recovered,
        "payments_recovered": snapshot.payments_recovered,
        "rollback_required": snapshot.rollback_required,
        "timeline": list(snapshot.timeline),
    }
