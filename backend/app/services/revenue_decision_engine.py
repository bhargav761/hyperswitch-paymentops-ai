from dataclasses import dataclass


@dataclass(frozen=True)
class RevenueDecision:
    decision: str
    action: str
    target_connector: str | None
    traffic_shift_percent: int
    revenue_at_risk_per_hour: float
    expected_revenue_protected_per_hour: float
    intervention_risk: float
    blast_radius: float
    confidence: float
    rollback_required: bool
    reason: str
    reason_codes: tuple[str, ...]


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return round(max(minimum, min(maximum, value)), 2)


def decide_revenue_intervention(
    *,
    revenue_at_risk_per_hour: float,
    affected_payments: int,
    failure_rate: float,
    confidence: float,
    affected_connector: str | None,
    alternative_connector: str | None,
    alternative_connector_health: float = 0.0,
    current_connector_health: float = 0.0,
    requested_traffic_shift_percent: int = 35,
) -> RevenueDecision:
    revenue_at_risk = max(0.0, float(revenue_at_risk_per_hour))
    affected = max(0, int(affected_payments))
    failure_rate = _clamp(float(failure_rate))
    confidence = _clamp(float(confidence))
    alternative_health = _clamp(float(alternative_connector_health))
    current_health = _clamp(float(current_connector_health))
    shift = max(0, min(100, int(requested_traffic_shift_percent)))

    if revenue_at_risk <= 0 or affected == 0:
        return RevenueDecision(
            decision="OBSERVE",
            action="CONTINUE_OBSERVATION",
            target_connector=None,
            traffic_shift_percent=0,
            revenue_at_risk_per_hour=revenue_at_risk,
            expected_revenue_protected_per_hour=0.0,
            intervention_risk=0.0,
            blast_radius=0.0,
            confidence=confidence,
            rollback_required=False,
            reason="There is insufficient revenue exposure to justify intervention.",
            reason_codes=("NO_REVENUE_EXPOSURE",),
        )

    if (
        not alternative_connector
        or alternative_connector == affected_connector
        or alternative_health < 0.70
    ):
        return RevenueDecision(
            decision="OBSERVE",
            action="CONTINUE_OBSERVATION",
            target_connector=None,
            traffic_shift_percent=0,
            revenue_at_risk_per_hour=revenue_at_risk,
            expected_revenue_protected_per_hour=0.0,
            intervention_risk=_clamp(1.0 - alternative_health),
            blast_radius=0.0,
            confidence=confidence,
            rollback_required=False,
            reason=(
                "No sufficiently healthy alternative connector is available "
                "for a controlled intervention."
            ),
            reason_codes=("ALTERNATIVE_CONNECTOR_UNSAFE",),
        )

    intervention_risk = _clamp(
        (1.0 - alternative_health) * 0.50
        + (1.0 - confidence) * 0.30
        + current_health * 0.20
    )

    blast_radius = _clamp(shift / 100.0)

    protection_factor = _clamp(
        alternative_health
        * confidence
        * (1.0 - intervention_risk)
        * blast_radius
    )

    expected_protected = round(
        revenue_at_risk * protection_factor,
        2,
    )

    automatic_threshold = (
        confidence >= 0.80
        and alternative_health >= 0.85
        and failure_rate >= 0.20
        and intervention_risk <= 0.40
        and blast_radius <= 0.50
        and expected_protected > 0
    )

    if automatic_threshold:
        decision = "INTERVENE"
        action = "SHIFT_TRAFFIC"
        reason = (
            f"Shift {shift}% traffic from {affected_connector or 'current connector'} "
            f"to {alternative_connector}; expected revenue protected is "
            f"{expected_protected:.2f} per hour."
        )
        reason_codes = (
            "HIGH_REVENUE_EXPOSURE",
            "HEALTHY_ALTERNATIVE",
            "HIGH_CONFIDENCE",
            "CONTROLLED_BLAST_RADIUS",
        )
    else:
        decision = "APPROVAL_REQUIRED"
        action = "SHIFT_TRAFFIC"
        reason = (
            "Revenue exposure supports intervention, but deterministic "
            "guardrails require human approval before traffic is shifted."
        )
        reason_codes = (
            "REVENUE_INTERVENTION_CANDIDATE",
            "GUARDRAIL_APPROVAL_REQUIRED",
        )

    return RevenueDecision(
        decision=decision,
        action=action,
        target_connector=alternative_connector,
        traffic_shift_percent=shift,
        revenue_at_risk_per_hour=revenue_at_risk,
        expected_revenue_protected_per_hour=expected_protected,
        intervention_risk=intervention_risk,
        blast_radius=blast_radius,
        confidence=confidence,
        rollback_required=True,
        reason=reason,
        reason_codes=reason_codes,
    )
