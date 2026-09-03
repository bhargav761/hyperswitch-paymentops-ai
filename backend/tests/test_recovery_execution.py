import httpx

from app.recovery.policy_gateway import PolicyGateResult
from app.services.recovery_execution_service import (
    execute_policy_approved_recovery,
)


class FakeAdapter:
    def execute_retry(self, **kwargs):
        raise httpx.TimeoutException("timeout")

    def retrieve_payment(self, payment_id):
        raise httpx.ConnectError(
            "connection failed",
            request=httpx.Request("GET", "http://hyperswitch/payments"),
        )


def make_policy(action="RETRY_NOW", decision="ALLOW", allowed=True):
    return PolicyGateResult(
        decision=decision,
        action=action,
        allowed=allowed,
        requires_approval=False,
        idempotency_key="recovery:pay_test:" + action,
        reason_codes=("TEST",),
    )


def test_retry_provider_timeout_is_safe():
    result = execute_policy_approved_recovery(
        policy=make_policy(),
        payment_id="pay_test",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=FakeAdapter(),
    )

    assert result["executed"] is False
    assert result["status"] == "provider_timeout"
    assert result["error_code"] == "PROVIDER_TIMEOUT"
    assert result["success"] is False


def test_reconcile_provider_unavailable_is_safe():
    result = execute_policy_approved_recovery(
        policy=make_policy("RECONCILE"),
        payment_id="pay_test",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=FakeAdapter(),
    )

    assert result["executed"] is False
    assert result["status"] == "provider_unavailable"
    assert result["error_code"] == "PROVIDER_UNAVAILABLE"


def test_blocked_policy_never_executes_provider():
    class ExplodingAdapter:
        def execute_retry(self, **kwargs):
            raise AssertionError("provider must not be called")

    policy = make_policy(
        action="RETRY_NOW",
        decision="DENY",
        allowed=False,
    )

    result = execute_policy_approved_recovery(
        policy=policy,
        payment_id="pay_test",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=ExplodingAdapter(),
    )

    assert result["executed"] is False
    assert result["status"] == "blocked"
