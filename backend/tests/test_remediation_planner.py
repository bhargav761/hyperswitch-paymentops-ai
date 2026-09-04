from types import SimpleNamespace

from app.services.remediation_planner import (
    build_remediation_plan,
    evaluate_remediation_result,
)


def _decision(**overrides):
    values = {
        "decision": "INTERVENE",
        "action": "SHIFT_TRAFFIC",
        "target_connector": "connector_b",
        "traffic_shift_percent": 35,
        "expected_revenue_protected_per_hour": 1125000.0,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_remediation_plan_is_executable_and_safe():
    plan = build_remediation_plan(
        decision=_decision(),
        observation_window_seconds=300,
    )

    assert plan.plan_id.startswith("PLAN-")
    assert plan.action == "SHIFT_TRAFFIC"
    assert plan.target_connector == "connector_b"
    assert plan.traffic_shift_percent == 35
    assert plan.observation_window_seconds == 300
    assert plan.status == "READY_FOR_POLICY_VALIDATION"
    assert len(plan.steps) >= 4
    assert len(plan.success_criteria) == 4
    assert len(plan.rollback_triggers) == 4
    assert "Restore traffic" in plan.rollback_action


def test_non_actionable_decision_does_not_create_intervention():
    plan = build_remediation_plan(
        decision=_decision(
            decision="OBSERVE",
            action="CONTINUE_OBSERVATION",
            target_connector=None,
            traffic_shift_percent=0,
            expected_revenue_protected_per_hour=0.0,
        )
    )

    assert plan.status == "NOT_ACTIONABLE"
    assert plan.action == "CONTINUE_OBSERVATION"
    assert plan.target_connector is None
    assert plan.traffic_shift_percent == 0
    assert plan.expected_revenue_protected_per_hour == 0.0


def test_successful_remediation_is_verified():
    plan = build_remediation_plan(decision=_decision())

    result = evaluate_remediation_result(
        plan=plan,
        failure_rate=0.05,
        average_latency_ms=900,
        connector_health=0.92,
        revenue_at_risk_per_hour=200000,
        previous_revenue_at_risk_per_hour=1500000,
    )

    assert result["status"] == "VERIFIED"
    assert result["success"] is True
    assert result["rollback_required"] is False


def test_failed_remediation_requires_rollback():
    plan = build_remediation_plan(decision=_decision())

    result = evaluate_remediation_result(
        plan=plan,
        failure_rate=0.35,
        average_latency_ms=3500,
        connector_health=0.40,
        revenue_at_risk_per_hour=1800000,
        previous_revenue_at_risk_per_hour=1500000,
    )

    assert result["status"] == "ROLLBACK_REQUIRED"
    assert result["success"] is False
    assert result["rollback_required"] is True
