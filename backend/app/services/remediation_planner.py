from dataclasses import dataclass


@dataclass(frozen=True)
class RemediationPlan:
    plan_id: str
    decision: str
    action: str
    target_connector: str | None
    traffic_shift_percent: int
    observation_window_seconds: int
    steps: tuple[str, ...]
    success_criteria: tuple[str, ...]
    rollback_triggers: tuple[str, ...]
    rollback_action: str
    expected_revenue_protected_per_hour: float
    status: str


def build_remediation_plan(
    *,
    decision,
    observation_window_seconds: int = 300,
    success_failure_rate: float = 0.10,
    success_latency_ms: float = 2000.0,
) -> RemediationPlan:
    plan_id = "PLAN-" + str(
        abs(
            hash(
                (
                    decision.action,
                    decision.target_connector,
                    decision.traffic_shift_percent,
                    decision.expected_revenue_protected_per_hour,
                )
            )
        ) % 10**8
    ).zfill(8)


    if decision.decision not in {"INTERVENE", "APPROVAL_REQUIRED"}:
        return RemediationPlan(
            plan_id=plan_id,
            decision=decision.decision,
            action="CONTINUE_OBSERVATION",
            target_connector=None,
            traffic_shift_percent=0,
            observation_window_seconds=observation_window_seconds,
            steps=("Continue payment telemetry observation.",),
            success_criteria=("No intervention required.",),
            rollback_triggers=("New systemic degradation detected.",),
            rollback_action="NO_ACTION",
            expected_revenue_protected_per_hour=0.0,
            status="NOT_ACTIONABLE",
        )

    target = decision.target_connector or "unknown"

    steps = (
        "Validate deterministic policy and guardrails.",
        f"Shift {decision.traffic_shift_percent}% traffic to {target}.",
        f"Observe payment telemetry for {observation_window_seconds} seconds.",
        "Compare payment success rate and latency against the pre-intervention baseline.",
        "Verify connector health and revenue exposure.",
    )

    success_criteria = (
        f"Failure rate <= {success_failure_rate:.2f}.",
        f"Average latency <= {success_latency_ms:.0f} ms.",
        "Target connector remains healthy.",
        "Revenue at risk decreases after intervention.",
    )

    rollback_triggers = (
        f"Failure rate > {success_failure_rate:.2f} during observation.",
        f"Average latency > {success_latency_ms:.0f} ms during observation.",
        "Target connector health falls below safe threshold.",
        "Revenue exposure increases after intervention.",
    )

    return RemediationPlan(
        plan_id=plan_id,
        decision=decision.decision,
        action=decision.action,
        target_connector=target,
        traffic_shift_percent=decision.traffic_shift_percent,
        observation_window_seconds=observation_window_seconds,
        steps=steps,
        success_criteria=success_criteria,
        rollback_triggers=rollback_triggers,
        rollback_action=(
            f"Restore traffic to the original connector and re-evaluate "
            f"payment telemetry."
        ),
        expected_revenue_protected_per_hour=(
            decision.expected_revenue_protected_per_hour
        ),
        status="READY_FOR_POLICY_VALIDATION",
    )


def evaluate_remediation_result(
    *,
    plan: RemediationPlan,
    failure_rate: float,
    average_latency_ms: float,
    connector_health: float,
    revenue_at_risk_per_hour: float,
    previous_revenue_at_risk_per_hour: float,
) -> dict:
    success = (
        failure_rate <= 0.10
        and average_latency_ms <= 2000.0
        and connector_health >= 0.70
        and revenue_at_risk_per_hour < previous_revenue_at_risk_per_hour
    )

    if success:
        return {
            "status": "VERIFIED",
            "success": True,
            "rollback_required": False,
            "reason": "Remediation success criteria were satisfied.",
        }

    return {
        "status": "ROLLBACK_REQUIRED",
        "success": False,
        "rollback_required": True,
        "reason": "One or more remediation success criteria failed.",
    }
