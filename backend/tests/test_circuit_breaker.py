from app.routing.circuit_breaker import ConnectorCircuitBreaker


def test_circuit_opens_after_failure_threshold():
    breaker = ConnectorCircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=60,
    )

    assert breaker.is_open("stripe") is False

    breaker.record_failure("stripe")
    assert breaker.is_open("stripe") is False

    breaker.record_failure("stripe")
    assert breaker.is_open("stripe") is True


def test_success_resets_circuit():
    breaker = ConnectorCircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=60,
    )

    breaker.record_failure("stripe")
    breaker.record_failure("stripe")
    assert breaker.is_open("stripe") is True

    breaker.record_success("stripe")
    assert breaker.is_open("stripe") is False


def test_open_connector_is_filtered():
    breaker = ConnectorCircuitBreaker(
        failure_threshold=1,
        recovery_timeout_seconds=60,
    )

    breaker.record_failure("stripe")

    connectors = [
        {"name": "stripe", "enabled": True},
        {"name": "adyen", "enabled": True},
    ]

    filtered = breaker.filter_connectors(connectors)

    assert [item["name"] for item in filtered] == ["adyen"]


def test_snapshot_reports_state():
    breaker = ConnectorCircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=60,
    )

    breaker.record_failure("stripe")

    snapshot = breaker.snapshot()

    assert snapshot["stripe"]["failures"] == 1
    assert snapshot["stripe"]["open"] is False
