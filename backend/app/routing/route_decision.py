from app.routing.load_balancer import select_healthy_connector


def decide_route(
    *,
    connectors: list[dict],
    current_connector: str | None = None,
    failure_code: str | None = None,
) -> dict:
    selected = select_healthy_connector(connectors)

    if selected is None:
        return {
            "decision": "NO_ROUTE",
            "connector": None,
            "reason": "No healthy connector is available.",
        }

    if current_connector and selected["name"] != current_connector:
        return {
            "decision": "REROUTE",
            "connector": selected["name"],
            "reason": (
                f"Selected healthier connector after payment failure: "
                f"{failure_code or 'payment_failure'}."
            ),
        }

    return {
        "decision": "KEEP_ROUTE",
        "connector": selected["name"],
        "reason": "Current route is healthy enough to continue.",
    }
