from types import SimpleNamespace

from app.services.gitops_controller import (
    build_argo_rollout,
    build_gitops_change,
    validate_gitops_change,
)


def _plan(**overrides):
    values = {
        "plan_id": "PLAN-12345678",
        "target_connector": "connector_b",
        "traffic_shift_percent": 35,
        "rollback_action": "Restore traffic to connector_a.",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_gitops_change_passes_deterministic_validation():
    result = validate_gitops_change(
        target_connector="connector_b",
        traffic_shift_percent=35,
        confidence=0.94,
        intervention_risk=0.20,
        blast_radius=0.35,
    )

    assert result.allowed is True
    assert result.status == "APPROVED"
    assert "TRAFFIC_SHIFT_BOUNDED" in result.reason_codes


def test_gitops_change_blocks_unsafe_traffic_shift():
    result = validate_gitops_change(
        target_connector="connector_b",
        traffic_shift_percent=75,
        confidence=0.95,
        intervention_risk=0.10,
        blast_radius=0.75,
    )

    assert result.allowed is False
    assert result.status == "BLOCKED"
    assert "TRAFFIC_SHIFT_OUT_OF_BOUNDS" in result.reason_codes


def test_gitops_change_generates_argo_ready_change():
    change = build_gitops_change(plan=_plan(), confidence=0.94, intervention_risk=0.20)

    assert change.change_id == "CHANGE-12345678"
    assert change.repository == "paymentops-infrastructure"
    assert change.manifest_path.endswith("payment-routing.yaml")
    assert change.validation_status == "APPROVED"
    assert change.rollout_strategy == "ARGO_CANARY"


def test_argo_rollout_requires_validation():
    change = build_gitops_change(plan=_plan(), confidence=0.94, intervention_risk=0.20)

    rollout = build_argo_rollout(
        change=change,
        observation_window_seconds=300,
    )

    assert rollout["status"] == "READY"
    assert rollout["controller"] == "argo-rollouts"
    assert rollout["verification_required"] is True
    assert rollout["traffic_shift_percent"] == 35
    assert rollout["observation_window_seconds"] == 300
