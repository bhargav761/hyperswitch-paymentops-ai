def calculate_connector_health(
    *,
    success_rate: float,
    latency_ms: float,
    failure_rate: float,
) -> float:
    success_rate = max(0.0, min(1.0, success_rate))
    failure_rate = max(0.0, min(1.0, failure_rate))

    latency_score = max(0.0, min(1.0, 1.0 - (latency_ms / 5000.0)))

    score = (
        success_rate * 0.60
        + latency_score * 0.25
        + (1.0 - failure_rate) * 0.15
    )

    return round(score, 4)
