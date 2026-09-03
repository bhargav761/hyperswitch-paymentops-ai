from app.routing.health_score import calculate_connector_health
from app.routing.load_balancer import select_healthy_connector
from app.routing.route_decision import decide_route


def test_health_score_is_bounded():
    score = calculate_connector_health(
        success_rate=0.95,
        latency_ms=200,
        failure_rate=0.05,
    )

    assert 0.0 <= score <= 1.0
    assert score > 0.80


def test_load_balancer_selects_healthiest_connector():
    connectors = [
        {"name": "connector_a", "health_score": 0.70, "latency_ms": 400},
        {"name": "connector_b", "health_score": 0.92, "latency_ms": 250},
    ]

    selected = select_healthy_connector(connectors)

    assert selected["name"] == "connector_b"


def test_load_balancer_rejects_unhealthy_connectors():
    connectors = [
        {"name": "connector_a", "health_score": 0.30},
        {"name": "connector_b", "health_score": 0.40},
    ]

    assert select_healthy_connector(connectors) is None


def test_route_decision_reroutes_to_healthier_connector():
    result = decide_route(
        connectors=[
            {"name": "stripe", "health_score": 0.45, "latency_ms": 900},
            {"name": "razorpay", "health_score": 0.91, "latency_ms": 200},
        ],
        current_connector="stripe",
        failure_code="network_timeout",
    )

    assert result["decision"] == "REROUTE"
    assert result["connector"] == "razorpay"


def test_route_decision_keeps_healthy_route():
    result = decide_route(
        connectors=[
            {"name": "razorpay", "health_score": 0.91, "latency_ms": 200},
        ],
        current_connector="razorpay",
    )

    assert result["decision"] == "KEEP_ROUTE"
    assert result["connector"] == "razorpay"


def test_route_decision_handles_no_healthy_connector():
    result = decide_route(
        connectors=[
            {"name": "stripe", "health_score": 0.20},
        ],
        current_connector="stripe",
    )

    assert result["decision"] == "NO_ROUTE"
    assert result["connector"] is None
