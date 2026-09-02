def build_recovery_key(
    payment_id: str,
    action: str,
) -> str:
    return f"recovery:{payment_id}:{action}"
