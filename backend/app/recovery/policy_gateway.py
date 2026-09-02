from dataclasses import dataclass

from app.recovery.idempotency import build_recovery_key
from app.recovery.policy_engine import is_retry_allowed


@dataclass(frozen=True)
class PolicyGateResult:
    decision: str
    action: str
    allowed: bool
    requires_approval: bool
    idempotency_key: str
    reason_codes: tuple[str, ...]


def evaluate_policy_gate(
    payment_id: str,
    amount: float,
    action: str,
    confidence: float,
    retry_count: int = 0,
) -> PolicyGateResult:
    """Evaluate whether a recommended recovery action is policy-safe."""

    idempotency_key = build_recovery_key(payment_id, action)

    if action in {"RETRY_NOW", "RETRY_LATER"}:
        if not is_retry_allowed(
            amount=amount,
            confidence=confidence,
            retry_count=retry_count,
        ):
            return PolicyGateResult(
                decision="DENY",
                action=action,
                allowed=False,
                requires_approval=False,
                idempotency_key=idempotency_key,
                reason_codes=("RETRY_POLICY_BLOCKED",),
            )

        return PolicyGateResult(
            decision="ALLOW",
            action=action,
            allowed=True,
            requires_approval=False,
            idempotency_key=idempotency_key,
            reason_codes=(
                "RETRY_POLICY_ALLOWED",
                "IDEMPOTENCY_KEY_GENERATED",
            ),
        )

    if action == "HUMAN_REVIEW":
        return PolicyGateResult(
            decision="APPROVAL_REQUIRED",
            action=action,
            allowed=False,
            requires_approval=True,
            idempotency_key=idempotency_key,
            reason_codes=("HUMAN_APPROVAL_REQUIRED",),
        )

    if action in {"RECONCILE", "ALTERNATIVE_PAYMENT"}:
        return PolicyGateResult(
            decision="ALLOW",
            action=action,
            allowed=True,
            requires_approval=False,
            idempotency_key=idempotency_key,
            reason_codes=(
                "ACTION_POLICY_ALLOWED",
                "IDEMPOTENCY_KEY_GENERATED",
            ),
        )

    return PolicyGateResult(
        decision="DENY",
        action=action,
        allowed=False,
        requires_approval=False,
        idempotency_key=idempotency_key,
        reason_codes=("UNKNOWN_ACTION",),
    )
