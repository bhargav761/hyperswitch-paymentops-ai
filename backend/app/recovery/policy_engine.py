from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryPolicy:
    max_retry_attempts: int = 2
    min_confidence: float = 0.70
    max_amount_for_auto_retry: float = 100000.0


DEFAULT_POLICY = RecoveryPolicy()


def is_retry_allowed(
    amount: float,
    confidence: float,
    retry_count: int,
) -> bool:
    return (
        retry_count < DEFAULT_POLICY.max_retry_attempts
        and confidence >= DEFAULT_POLICY.min_confidence
        and amount <= DEFAULT_POLICY.max_amount_for_auto_retry
    )
