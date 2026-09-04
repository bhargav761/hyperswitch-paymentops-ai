from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    status: str
    success: bool
    rollback_required: bool
    failure_rate_before: float
    failure_rate_after: float
    latency_before_ms: float
    latency_after_ms: float
    revenue_at_risk_before_per_hour: float
    revenue_at_risk_after_per_hour: float
    revenue_protected_per_hour: float
    revenue_recovered: float
    payments_recovered: int
    reason: str


def verify_recovery(
    *,
    failure_rate_before: float,
    failure_rate_after: float,
    latency_before_ms: float,
    latency_after_ms: float,
    revenue_at_risk_before_per_hour: float,
    revenue_at_risk_after_per_hour: float,
    payments_recovered: int = 0,
    success_failure_rate: float = 0.10,
    success_latency_ms: float = 2000.0,
) -> VerificationResult:
    before_revenue = max(0.0, float(revenue_at_risk_before_per_hour))
    after_revenue = max(0.0, float(revenue_at_risk_after_per_hour))

    revenue_protected = round(
        max(0.0, before_revenue - after_revenue),
        2,
    )

    recovered = max(0, int(payments_recovered))

    success = (
        float(failure_rate_after) <= success_failure_rate
        and float(latency_after_ms) <= success_latency_ms
        and after_revenue < before_revenue
    )

    if success:
        return VerificationResult(
            status="VERIFIED",
            success=True,
            rollback_required=False,
            failure_rate_before=float(failure_rate_before),
            failure_rate_after=float(failure_rate_after),
            latency_before_ms=float(latency_before_ms),
            latency_after_ms=float(latency_after_ms),
            revenue_at_risk_before_per_hour=before_revenue,
            revenue_at_risk_after_per_hour=after_revenue,
            revenue_protected_per_hour=revenue_protected,
            revenue_recovered=revenue_protected,
            payments_recovered=recovered,
            reason="Recovery improved payment reliability and reduced revenue exposure.",
        )

    return VerificationResult(
        status="ROLLBACK_REQUIRED",
        success=False,
        rollback_required=True,
        failure_rate_before=float(failure_rate_before),
        failure_rate_after=float(failure_rate_after),
        latency_before_ms=float(latency_before_ms),
        latency_after_ms=float(latency_after_ms),
        revenue_at_risk_before_per_hour=before_revenue,
        revenue_at_risk_after_per_hour=after_revenue,
        revenue_protected_per_hour=revenue_protected,
        revenue_recovered=0.0,
        payments_recovered=recovered,
        reason="Recovery success criteria were not satisfied; rollback is required.",
    )
