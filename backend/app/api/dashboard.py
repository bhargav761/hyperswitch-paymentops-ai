from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment
from app.services.risk_service import calculate_revenue_at_risk

router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["dashboard"],
)


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    payments = db.query(Payment).all()

    total_payments = len(payments)
    successful = sum(1 for p in payments if p.status == "success")
    failed = sum(1 for p in payments if p.status == "failed")
    pending = sum(1 for p in payments if p.status == "pending")

    revenue_at_risk = sum(
        (
            calculate_revenue_at_risk(
                p.amount,
                p.status,
                p.failure_code,
            )
            for p in payments
        ),
        Decimal("0.00"),
    )

    failed_or_pending_value = sum(
        (
            p.amount
            for p in payments
            if p.status in {"failed", "pending"}
        ),
        Decimal("0.00"),
    )

    success_rate = (
        round((successful / total_payments) * 100, 2)
        if total_payments
        else 0
    )

    return {
        "total_payments": total_payments,
        "successful_payments": successful,
        "failed_payments": failed,
        "pending_payments": pending,
        "success_rate_percent": success_rate,
        "failed_or_pending_value": failed_or_pending_value,
        "revenue_at_risk": revenue_at_risk,
    }
