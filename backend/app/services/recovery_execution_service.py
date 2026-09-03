import httpx

from app.integrations.hyperswitch.adapter import HyperswitchAdapter
from app.integrations.hyperswitch.client import HyperswitchClient
from app.recovery.policy_gateway import PolicyGateResult
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def build_hyperswitch_adapter(
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
) -> HyperswitchAdapter:
    client = HyperswitchClient(
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )
    return HyperswitchAdapter(client)


def execute_policy_approved_recovery(
    *,
    policy: PolicyGateResult,
    payment_id: str,
    amount: float,
    currency: str,
    payment_method: str,
    connector: str | None,
    adapter: HyperswitchAdapter,
) -> dict:
    """Execute only recovery actions explicitly authorized by policy."""

    if policy.decision != "ALLOW" or not policy.allowed:
        logger.warning(
            "recovery.execution.blocked payment_id=%s action=%s decision=%s",
            payment_id,
            policy.action,
            policy.decision,
        )
        return {
            "executed": False,
            "status": (
                "approval_required"
                if policy.requires_approval
                else "blocked"
            ),
            "action": policy.action,
            "message": "Recovery execution was blocked by the policy gateway.",
            "idempotency_key": policy.idempotency_key,
        }

    try:
        if policy.action == "RETRY_NOW":
            result = adapter.execute_retry(
                payment_id=payment_id,
                amount=amount,
                currency=currency,
                payment_method=payment_method,
                idempotency_key=policy.idempotency_key,
                connector=connector,
            )

            return {
                "executed": True,
                "status": result.status,
                "action": policy.action,
                "success": result.success,
                "payment_id": result.payment_id,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "idempotency_key": policy.idempotency_key,
                "provider_response": result.raw,
            }

        if policy.action == "RECONCILE":
            result = adapter.retrieve_payment(payment_id)

            return {
                "executed": True,
                "status": result.status,
                "action": policy.action,
                "success": result.success,
                "payment_id": result.payment_id,
                "error_code": result.error_code,
                "error_message": result.error_message,
                "idempotency_key": policy.idempotency_key,
                "provider_response": result.raw,
            }

        return {
            "executed": False,
            "status": "unsupported",
            "action": policy.action,
            "message": (
                "The policy action is allowed but has no configured "
                "Hyperswitch execution adapter."
            ),
            "idempotency_key": policy.idempotency_key,
        }

    except httpx.TimeoutException:
        logger.error(
            "recovery.execution.timeout payment_id=%s action=%s",
            payment_id,
            policy.action,
        )
        return {
            "executed": False,
            "status": "provider_timeout",
            "action": policy.action,
            "success": False,
            "payment_id": payment_id,
            "error_code": "PROVIDER_TIMEOUT",
            "error_message": "Hyperswitch request timed out.",
            "idempotency_key": policy.idempotency_key,
        }

    except httpx.HTTPStatusError as exc:
        logger.error(
            "recovery.execution.http_error payment_id=%s action=%s status=%s",
            payment_id,
            policy.action,
            exc.response.status_code,
        )
        return {
            "executed": False,
            "status": "provider_error",
            "action": policy.action,
            "success": False,
            "payment_id": payment_id,
            "error_code": f"PROVIDER_HTTP_{exc.response.status_code}",
            "error_message": "Hyperswitch rejected the recovery request.",
            "idempotency_key": policy.idempotency_key,
        }

    except httpx.RequestError:
        logger.error(
            "recovery.execution.request_error payment_id=%s action=%s",
            payment_id,
            policy.action,
        )
        return {
            "executed": False,
            "status": "provider_unavailable",
            "action": policy.action,
            "success": False,
            "payment_id": payment_id,
            "error_code": "PROVIDER_UNAVAILABLE",
            "error_message": "Hyperswitch could not be reached.",
            "idempotency_key": policy.idempotency_key,
        }
