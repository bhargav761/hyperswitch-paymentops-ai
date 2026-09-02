def severity_from_score(score: float) -> str:
    if score >= 0.85:
        return "critical"
    if score >= 0.70:
        return "high"
    if score >= 0.50:
        return "medium"
    return "low"


def recovery_priority(
    risk_score: float,
    revenue_at_risk: float,
) -> float:
    value_factor = min(
        revenue_at_risk / 10000.0,
        1.0,
    )

    priority = (
        risk_score * 0.70
        + value_factor * 0.30
    )

    return round(
        min(priority, 1.0),
        2,
    )
