from dataclasses import dataclass

from app.recovery.policy_engine import is_retry_allowed


@dataclass
class RecoveryDecision:
    action: str
    confidence: float
    reason: str
    requires_approval: bool


def decide_recovery(
    amount: float,
    root_cause: str,
    risk_score: float,
    retry_count: int = 0,
) -> RecoveryDecision:

    if root_cause == "payment_network_degradation":
        confidence = min(
            0.95,
            0.70 + risk_score * 0.20,
        )

        if is_retry_allowed(
            amount,
            confidence,
            retry_count,
        ):
            return RecoveryDecision(
                action="reroute_or_retry",
                confidence=round(confidence, 2),
                reason=(
                    "Network degradation detected; "
                    "bounded retry or alternate route is appropriate."
                ),
                requires_approval=False,
            )

    if root_cause == "payment_timeout":
        confidence = 0.82

        if is_retry_allowed(
            amount,
            confidence,
            retry_count,
        ):
            return RecoveryDecision(
                action="retry_with_backoff",
                confidence=confidence,
                reason=(
                    "Payment timeout detected; "
                    "retry with controlled backoff."
                ),
                requires_approval=False,
            )

    if root_cause == "payment_pending":
        return RecoveryDecision(
            action="verify_payment_state",
            confidence=0.90,
            reason=(
                "Payment is pending; verify final state "
                "before attempting another charge."
            ),
            requires_approval=False,
        )

    if root_cause == "issuer_decline":
        return RecoveryDecision(
            action="alternative_payment_method",
            confidence=0.88,
            reason=(
                "Issuer decline detected; avoid blind retries "
                "and offer an alternative payment method."
            ),
            requires_approval=False,
        )

    return RecoveryDecision(
        action="manual_review",
        confidence=0.50,
        reason=(
            "Automatic recovery is not sufficiently safe "
            "for this condition."
        ),
        requires_approval=True,
    )
