from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment
from app.schemas.payment import PaymentEvent
from app.services.logging_service import get_logger
from app.services.payment_service import list_payments

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/payments",
    tags=["payments"],
)


@router.post("/events")
def receive_payment_event(
    event: PaymentEvent,
    db: Session = Depends(get_db),
):
    existing = (
        db.query(Payment)
        .filter(Payment.event_id == event.event_id)
        .first()
    )

    if existing:
        logger.info(
            "payment.duplicate payment_id=%s event_id=%s",
            existing.payment_id,
            event.event_id,
        )

        return {
            "accepted": True,
            "duplicate": True,
            "payment_id": existing.payment_id,
            "status": existing.status,
        }

    payment = Payment(
        payment_id=event.payment_id,
        event_id=event.event_id,
        amount=event.amount,
        currency=event.currency.upper(),
        method=event.method,
        connector=event.connector,
        region=event.region,
        status=event.status.lower(),
        failure_code=event.failure_code,
        failure_reason=event.failure_reason,
        latency_ms=event.latency_ms,
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    logger.info(
        "payment.received payment_id=%s event_id=%s status=%s amount=%s",
        payment.payment_id,
        payment.event_id,
        payment.status,
        payment.amount,
    )

    return {
        "accepted": True,
        "duplicate": False,
        "payment_id": payment.payment_id,
        "status": payment.status,
    }


@router.get("")
def get_payments(
    db: Session = Depends(get_db),
):
    return list_payments(db)
