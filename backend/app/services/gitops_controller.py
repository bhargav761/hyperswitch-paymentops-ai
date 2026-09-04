from dataclasses import dataclass


@dataclass(frozen=True)
class GitOpsChange:
    change_id: str
    plan_id: str
    repository: str
    manifest_path: str
    target_connector: str | None
    traffic_shift_percent: int
    commit_message: str
    validation_status: str
    rollout_strategy: str
    rollback_strategy: str


@dataclass(frozen=True)
class GitOpsValidation:
    allowed: bool
    status: str
    reason_codes: tuple[str, ...]
    message: str


def validate_gitops_change(
    *,
    target_connector: str | None,
    traffic_shift_percent: int,
    confidence: float,
    intervention_risk: float,
    blast_radius: float,
) -> GitOpsValidation:
    if not target_connector:
        return GitOpsValidation(
            allowed=False,
            status="BLOCKED",
            reason_codes=("TARGET_CONNECTOR_MISSING",),
            message="GitOps change requires a target connector.",
        )

    if traffic_shift_percent <= 0 or traffic_shift_percent > 50:
        return GitOpsValidation(
            allowed=False,
            status="BLOCKED",
            reason_codes=("TRAFFIC_SHIFT_OUT_OF_BOUNDS",),
            message="Automatic traffic shifts must remain within 1-50%.",
        )

    if confidence < 0.80:
        return GitOpsValidation(
            allowed=False,
            status="BLOCKED",
            reason_codes=("INSUFFICIENT_CONFIDENCE",),
            message="Confidence is below the automatic rollout threshold.",
        )

    if intervention_risk > 0.40:
        return GitOpsValidation(
            allowed=False,
            status="BLOCKED",
            reason_codes=("INTERVENTION_RISK_TOO_HIGH",),
            message="Intervention risk exceeds the automatic rollout threshold.",
        )

    if blast_radius > 0.50:
        return GitOpsValidation(
            allowed=False,
            status="BLOCKED",
            reason_codes=("BLAST_RADIUS_TOO_HIGH",),
            message="Blast radius exceeds the automatic rollout threshold.",
        )

    return GitOpsValidation(
        allowed=True,
        status="APPROVED",
        reason_codes=(
            "TARGET_CONNECTOR_VALID",
            "TRAFFIC_SHIFT_BOUNDED",
            "CONFIDENCE_ACCEPTABLE",
            "INTERVENTION_RISK_ACCEPTABLE",
            "BLAST_RADIUS_ACCEPTABLE",
        ),
        message="GitOps change passed deterministic rollout validation.",
    )


def build_gitops_change(
    *,
    plan,
    confidence: float = 0.90,
    intervention_risk: float = 0.20,
    repository: str = "paymentops-infrastructure",
    manifest_path: str = "deploy/traffic/payment-routing.yaml",
) -> GitOpsChange:
    validation = validate_gitops_change(
        target_connector=plan.target_connector,
        traffic_shift_percent=plan.traffic_shift_percent,
        confidence=confidence,
        intervention_risk=intervention_risk,
        blast_radius=plan.traffic_shift_percent / 100.0,
    )

    change_id = f"CHANGE-{plan.plan_id.removeprefix('PLAN-')}"

    return GitOpsChange(
        change_id=change_id,
        plan_id=plan.plan_id,
        repository=repository,
        manifest_path=manifest_path,
        target_connector=plan.target_connector,
        traffic_shift_percent=plan.traffic_shift_percent,
        commit_message=(
            f"ops: shift {plan.traffic_shift_percent}% traffic "
            f"to {plan.target_connector}"
        ),
        validation_status=validation.status,
        rollout_strategy="ARGO_CANARY",
        rollback_strategy=plan.rollback_action,
    )


def build_argo_rollout(
    *,
    change: GitOpsChange,
    observation_window_seconds: int,
) -> dict:
    if change.validation_status != "APPROVED":
        return {
            "status": "BLOCKED",
            "change_id": change.change_id,
            "message": "Argo rollout blocked because GitOps validation failed.",
        }

    return {
        "status": "READY",
        "change_id": change.change_id,
        "controller": "argo-rollouts",
        "strategy": change.rollout_strategy,
        "observation_window_seconds": observation_window_seconds,
        "target_connector": change.target_connector,
        "traffic_shift_percent": change.traffic_shift_percent,
        "rollback_strategy": change.rollback_strategy,
        "verification_required": True,
    }
