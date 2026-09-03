def select_healthy_connector(
    connectors: list[dict],
    *,
    minimum_health: float = 0.50,
) -> dict | None:
    eligible = [
        connector
        for connector in connectors
        if connector.get("enabled", True)
        and connector.get("health_score", 0.0) >= minimum_health
    ]

    if not eligible:
        return None

    return max(
        eligible,
        key=lambda connector: (
            connector.get("health_score", 0.0),
            -connector.get("latency_ms", float("inf")),
        ),
    )
