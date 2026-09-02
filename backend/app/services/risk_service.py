from decimal import Decimal

from app.risk.revenue_risk import calculate_revenue_at_risk as _calculate


def calculate_revenue_at_risk(
    amount: Decimal,
    status: str,
    failure_code: str | None = None,
) -> Decimal:
    return _calculate(
        amount=amount,
        status=status,
        failure_code=failure_code,
    )
