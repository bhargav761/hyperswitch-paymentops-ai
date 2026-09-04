import httpx

from app.routing.circuit_breaker import ConnectorCircuitBreaker
from app.services.recovery_execution_service import execute_policy_approved_recovery
from app.recovery.policy_gateway import PolicyGateResult


def make_policy():
    return PolicyGateResult(
        decision="ALLOW",
        action="RETRY_NOW",
        allowed=True,
        requires_approval=False,
        idempotency_key="recovery:resilience:RETRY_NOW",
        reason_codes=("TEST",),
    )


def test_circuit_breaker_prevents_unhealthy_connector():
    breaker = ConnectorCircuitBreaker(
        failure_threshold=2,
        recovery_timeout_seconds=60,
    )

    breaker.record_failure("stripe")
    breaker.record_failure("stripe")

    connectors = [
        {"name": "stripe", "health_score": 0.95, "enabled": True},
        {"name": "adyen", "health_score": 0.80, "enabled": True},
    ]

    filtered = breaker.filter_connectors(connectors)

    assert [item["name"] for item in filtered] == ["adyen"]


def test_provider_timeout_does_not_report_success():
    class TimeoutAdapter:
        def execute_retry(self, **kwargs):
            raise httpx.TimeoutException("timeout")

    result = execute_policy_approved_recovery(
        policy=make_policy(),
        payment_id="resilience-timeout",
        amount=100,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=TimeoutAdapter(),
    )

    assert result["success"] is False
    assert result["executed"] is False
    assert result["status"] == "provider_timeout"


def test_provider_http_failure_does_not_report_success():
    class HTTPFailureAdapter:
        def execute_retry(self, **kwargs):
            request = httpx.Request(
                "POST",
                "http://hyperswitch/payments",
            )
            response = httpx.Response(
                503,
                request=request,
            )
            raise httpx.HTTPStatusError(
                "provider unavailable",
                request=request,
                response=response,
            )

    result = execute_policy_approved_recovery(
        policy=make_policy(),
        payment_id="resilience-http",
        amount=100,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=HTTPFailureAdapter(),
    )

    assert result["success"] is False
    assert result["executed"] is False
    assert result["status"] == "provider_error"
    assert result["error_code"] == "PROVIDER_HTTP_503"
