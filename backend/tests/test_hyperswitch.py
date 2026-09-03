import json

import httpx

from app.integrations.hyperswitch.adapter import HyperswitchAdapter
from app.integrations.hyperswitch.client import HyperswitchClient


def test_hyperswitch_retry_normalizes_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/payments"
        assert request.headers["api-key"] == "test-key"
        assert request.headers["x-idempotency-key"] == (
            "recovery:pay_001:RETRY_NOW"
        )

        payload = json.loads(request.content)

        assert payload["payment_id"] == "pay_001"
        assert payload["amount"] == 4999
        assert payload["currency"] == "INR"
        assert payload["payment_method"] == "upi"
        assert payload["connector"] == "razorpay"

        return httpx.Response(
            200,
            json={
                "payment_id": "pay_001",
                "status": "succeeded",
            },
        )

    client = HyperswitchClient(
        base_url="http://hyperswitch.test",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    adapter = HyperswitchAdapter(client)

    result = adapter.execute_retry(
        payment_id="pay_001",
        amount=4999,
        currency="INR",
        payment_method="upi",
        idempotency_key="recovery:pay_001:RETRY_NOW",
        connector="razorpay",
    )

    assert result.success is True
    assert result.payment_id == "pay_001"
    assert result.status == "succeeded"


def test_hyperswitch_retrieve_normalizes_pending():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/payments/pay_002"

        return httpx.Response(
            200,
            json={
                "payment_id": "pay_002",
                "payment_status": "pending",
            },
        )

    client = HyperswitchClient(
        base_url="http://hyperswitch.test",
        transport=httpx.MockTransport(handler),
    )

    adapter = HyperswitchAdapter(client)

    result = adapter.retrieve_payment("pay_002")

    assert result.success is False
    assert result.payment_id == "pay_002"
    assert result.status == "pending"


def test_hyperswitch_failure_response_is_not_success():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "payment_id": "pay_003",
                "status": "failed",
                "error_code": "PMT_001",
                "error_message": "Payment failed",
            },
        )

    client = HyperswitchClient(
        base_url="http://hyperswitch.test",
        transport=httpx.MockTransport(handler),
    )

    adapter = HyperswitchAdapter(client)

    result = adapter.retrieve_payment("pay_003")

    assert result.success is False
    assert result.status == "failed"
    assert result.error_code == "PMT_001"
    assert result.error_message == "Payment failed"
