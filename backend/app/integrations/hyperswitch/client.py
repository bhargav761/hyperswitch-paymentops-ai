from typing import Any

import httpx


class HyperswitchClient:
    """Small HTTP client for the Hyperswitch payment-engine boundary."""

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["api-key"] = self.api_key

        return headers

    def _client(self) -> httpx.Client:
        return httpx.Client(
            transport=self.transport,
            timeout=self.timeout_seconds,
        )

    def create_payment(
        self,
        payload: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        headers = self._headers()

        if idempotency_key:
            headers["x-idempotency-key"] = idempotency_key

        with self._client() as client:
            response = client.post(
                f"{self.base_url}/payments",
                json=payload,
                headers=headers,
            )

        response.raise_for_status()
        return response.json()

    def retrieve_payment(
        self,
        payment_id: str,
    ) -> dict[str, Any]:
        with self._client() as client:
            response = client.get(
                f"{self.base_url}/payments/{payment_id}",
                headers=self._headers(),
            )

        response.raise_for_status()
        return response.json()
