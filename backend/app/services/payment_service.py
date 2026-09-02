from sqlalchemy.orm import Session

from app.models.payment import Payment
from app.services.logging_service import get_logger
from app.services.risk_service import calculate_revenue_at_risk

logger = get_logger(__name__)


def payment_to_response(payment: Payment) -> dict:
    return {
        "payment_id": payment.payment_id,
        "event_id": payment.event_id,
        "amount": payment.amount,
        "currency": payment.currency,
        "method": payment.method,
        "connector": payment.connector,
        "region": payment.region,
        "status": payment.status,
        "failure_code": payment.failure_code,
        "failure_reason": payment.failure_reason,
        "latency_ms": payment.latency_ms,
        "revenue_at_risk": calculate_revenue_at_risk(
            payment.amount,
            payment.status,
            payment.failure_code,
        ),
    }


def list_payments(db: Session) -> list[dict]:
    payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .all()
    )

    logger.info(
        "payments.list count=%s",
        len(payments),
    )

    return [
        payment_to_response(payment)
        for payment in payments
    ]
