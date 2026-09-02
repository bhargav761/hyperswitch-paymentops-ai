from decimal import Decimal


FAILURE_RECOVERY_PROBABILITY = {
    "timeout": Decimal("0.70"),
    "network_error": Decimal("0.65"),
    "issuer_decline": Decimal("0.25"),
    "insufficient_funds": Decimal("0.10"),
    "authentication_failed": Decimal("0.20"),
}


def calculate_revenue_at_risk(
    amount: Decimal,
    status: str,
    failure_code: str | None = None,
) -> Decimal:
    if status.lower() not in {"failed", "pending"}:
        return Decimal("0.00")

    normalized_code = (failure_code or "").lower()

    if status.lower() == "pending":
        probability = Decimal("0.80")
    else:
        probability = FAILURE_RECOVERY_PROBABILITY.get(
            normalized_code,
            Decimal("0.50"),
        )

    return (amount * probability).quantize(Decimal("0.01"))
