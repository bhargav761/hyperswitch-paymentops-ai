from app.services.closed_loop_verification import verify_recovery


def test_successful_recovery_measures_revenue_protected():
    result = verify_recovery(
        failure_rate_before=0.50,
        failure_rate_after=0.05,
        latency_before_ms=3500,
        latency_after_ms=900,
        revenue_at_risk_before_per_hour=1_500_000,
        revenue_at_risk_after_per_hour=250_000,
        payments_recovered=42,
    )

    assert result.status == "VERIFIED"
    assert result.success is True
    assert result.rollback_required is False
    assert result.revenue_protected_per_hour == 1_250_000
    assert result.revenue_recovered == 1_250_000
    assert result.payments_recovered == 42


def test_failed_recovery_requires_rollback():
    result = verify_recovery(
        failure_rate_before=0.50,
        failure_rate_after=0.35,
        latency_before_ms=3500,
        latency_after_ms=3200,
        revenue_at_risk_before_per_hour=1_500_000,
        revenue_at_risk_after_per_hour=1_800_000,
        payments_recovered=0,
    )

    assert result.status == "ROLLBACK_REQUIRED"
    assert result.success is False
    assert result.rollback_required is True
    assert result.revenue_protected_per_hour == 0.0
    assert result.revenue_recovered == 0.0


def test_verification_preserves_partial_revenue_improvement():
    result = verify_recovery(
        failure_rate_before=0.30,
        failure_rate_after=0.08,
        latency_before_ms=2800,
        latency_after_ms=1500,
        revenue_at_risk_before_per_hour=800_000,
        revenue_at_risk_after_per_hour=300_000,
        payments_recovered=15,
    )

    assert result.status == "VERIFIED"
    assert result.revenue_protected_per_hour == 500_000
    assert result.payments_recovered == 15
