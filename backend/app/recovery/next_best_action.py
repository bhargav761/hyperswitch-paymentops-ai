from dataclasses import dataclass


@dataclass(frozen=True)
class NextBestAction:
    action: str
    confidence: float
    reason: str
    requires_approval: bool
    delay_seconds: int | None
    reason_codes: tuple[str, ...]


def build_next_best_action(
    recovery_action: str,
    confidence: float,
    reason: str,
    requires_approval: bool,
    root_cause: str,
    risk_score: float,
) -> NextBestAction:

    normalized = recovery_action.lower().strip()

    recommendations = {
        "reroute_or_retry": (
            "RETRY_NOW",
            None,
            ("NETWORK_DEGRADATION", "RETRY_ELIGIBLE"),
        ),
        "retry_with_backoff": (
            "RETRY_LATER",
            1800,
            ("PAYMENT_TIMEOUT", "CONTROLLED_BACKOFF"),
        ),
        "verify_payment_state": (
            "RECONCILE",
            None,
            ("PAYMENT_PENDING", "STATE_VERIFICATION_REQUIRED"),
        ),
        "alternative_payment_method": (
            "ALTERNATIVE_PAYMENT",
            None,
            ("ISSUER_DECLINE", "AVOID_BLIND_RETRY"),
        ),
        "manual_review": (
            "HUMAN_REVIEW",
            None,
            ("AUTOMATIC_RECOVERY_UNSAFE",),
        ),
        "diagnose_before_retry": (
            "HUMAN_REVIEW",
            None,
            ("INSUFFICIENT_DIAGNOSTIC_CONFIDENCE",),
        ),
    }

    action, delay_seconds, reason_codes = recommendations.get(
        normalized,
        (
            "HUMAN_REVIEW",
            None,
            ("UNKNOWN_RECOVERY_ACTION",),
        ),
    )

    if risk_score >= 0.80 and action in {
        "RETRY_NOW",
        "RETRY_LATER",
    }:
        return NextBestAction(
            action="HUMAN_REVIEW",
            confidence=round(min(confidence, 0.70), 2),
            reason=(
                "Automatic retry was blocked because the "
                "payment risk score is high."
            ),
            requires_approval=True,
            delay_seconds=None,
            reason_codes=(
                "HIGH_RISK",
                "AUTO_RETRY_BLOCKED",
            ),
        )

    return NextBestAction(
        action=action,
        confidence=round(confidence, 2),
        reason=reason,
        requires_approval=requires_approval,
        delay_seconds=delay_seconds,
        reason_codes=reason_codes,
    )
