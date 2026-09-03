from typing import Any

from app.integrations.hyperswitch.client import HyperswitchClient
from app.integrations.hyperswitch.models import HyperswitchPaymentResult


class HyperswitchAdapter:
    """Provider boundary used by PaymentOps recovery execution."""

    def __init__(self, client: HyperswitchClient):
        self.client = client

    def execute_retry(
        self,
        *,
        payment_id: str,
        amount: float,
        currency: str,
        payment_method: str,
        idempotency_key: str,
        connector: str | None = None,
    ) -> HyperswitchPaymentResult:
        payload: dict[str, Any] = {
            "payment_id": payment_id,
            "amount": amount,
            "currency": currency,
            "payment_method": payment_method,
        }

        if connector:
            payload["connector"] = connector

        response = self.client.create_payment(
            payload,
            idempotency_key=idempotency_key,
        )

        return self._normalize_response(
            response=response,
            payment_id=payment_id,
        )

    def retrieve_payment(
        self,
        payment_id: str,
    ) -> HyperswitchPaymentResult:
        response = self.client.retrieve_payment(payment_id)

        return self._normalize_response(
            response=response,
            payment_id=payment_id,
        )

    @staticmethod
    def _normalize_response(
        *,
        response: dict[str, Any],
        payment_id: str,
    ) -> HyperswitchPaymentResult:
        status = str(
            response.get("status")
            or response.get("payment_status")
            or "unknown"
        ).lower()

        success = status in {
            "succeeded",
            "success",
            "charged",
            "completed",
        }

        return HyperswitchPaymentResult(
            success=success,
            payment_id=str(
                response.get("payment_id")
                or response.get("id")
                or payment_id
            ),
            status=status,
            raw=response,
            error_code=response.get("error_code"),
            error_message=response.get("error_message"),
        )
