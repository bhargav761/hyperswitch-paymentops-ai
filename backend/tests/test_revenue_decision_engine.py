from app.services.revenue_decision_engine import decide_revenue_intervention


def test_revenue_engine_recommends_controlled_traffic_shift():
    result = decide_revenue_intervention(
        revenue_at_risk_per_hour=1_500_000,
        affected_payments=5,
        failure_rate=0.50,
        confidence=0.94,
        affected_connector="connector_a",
        alternative_connector="connector_b",
        alternative_connector_health=0.95,
        current_connector_health=0.60,
        requested_traffic_shift_percent=35,
    )

    assert result.decision == "INTERVENE"
    assert result.action == "SHIFT_TRAFFIC"
    assert result.target_connector == "connector_b"
    assert result.traffic_shift_percent == 35
    assert result.expected_revenue_protected_per_hour > 0
    assert result.intervention_risk <= 0.40
    assert result.blast_radius == 0.35
    assert result.rollback_required is True


def test_revenue_engine_requires_approval_when_confidence_is_low():
    result = decide_revenue_intervention(
        revenue_at_risk_per_hour=1_500_000,
        affected_payments=10,
        failure_rate=0.40,
        confidence=0.60,
        affected_connector="connector_a",
        alternative_connector="connector_b",
        alternative_connector_health=0.95,
    )

    assert result.decision == "APPROVAL_REQUIRED"
    assert result.action == "SHIFT_TRAFFIC"
    assert result.rollback_required is True
    assert "GUARDRAIL_APPROVAL_REQUIRED" in result.reason_codes


def test_revenue_engine_observes_when_no_safe_alternative_exists():
    result = decide_revenue_intervention(
        revenue_at_risk_per_hour=1_500_000,
        affected_payments=10,
        failure_rate=0.40,
        confidence=0.95,
        affected_connector="connector_a",
        alternative_connector="connector_b",
        alternative_connector_health=0.55,
    )

    assert result.decision == "OBSERVE"
    assert result.action == "CONTINUE_OBSERVATION"
    assert result.target_connector is None
    assert result.expected_revenue_protected_per_hour == 0.0
    assert "ALTERNATIVE_CONNECTOR_UNSAFE" in result.reason_codes


def test_revenue_engine_observes_without_revenue_exposure():
    result = decide_revenue_intervention(
        revenue_at_risk_per_hour=0,
        affected_payments=0,
        failure_rate=0.0,
        confidence=0.95,
        affected_connector="connector_a",
        alternative_connector="connector_b",
        alternative_connector_health=0.95,
    )

    assert result.decision == "OBSERVE"
    assert result.action == "CONTINUE_OBSERVATION"
    assert result.rollback_required is False
