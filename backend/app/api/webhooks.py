from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment
from app.config.settings import WEBHOOK_SHARED_SECRET
from app.schemas.webhook import HyperswitchWebhookEvent
from app.services.logging_service import get_logger
from app.services.reconciliation_service import reconcile_recovery_outcome
from app.services.recovery_event_service import dispatch_recovery_event

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["webhooks"],
)


@router.post("/hyperswitch")
def receive_hyperswitch_webhook(
    event: HyperswitchWebhookEvent,
    db: Session = Depends(get_db),
    x_webhook_secret: str | None = Header(default=None),
):
    if WEBHOOK_SHARED_SECRET:
        if x_webhook_secret != WEBHOOK_SHARED_SECRET:
            logger.warning(
                "hyperswitch.webhook_unauthorized event_id=%s",
                event.event_id,
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid webhook authentication.",
            )

    existing_event = (
        db.query(Payment)
        .filter(Payment.event_id == event.event_id)
        .first()
    )

    if existing_event:
        logger.info(
            "hyperswitch.webhook_duplicate "
            "payment_id=%s event_id=%s",
            existing_event.payment_id,
            event.event_id,
        )

        return {
            "accepted": True,
            "duplicate": True,
            "payment_id": existing_event.payment_id,
            "status": existing_event.status,
        }

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == event.payment_id)
        .first()
    )

    if payment:
        if event.amount is not None:
            payment.amount = event.amount

        if event.currency is not None:
            payment.currency = event.currency.upper()

        if event.method is not None:
            payment.method = event.method

        if event.connector is not None:
            payment.connector = event.connector

        if event.region is not None:
            payment.region = event.region

        payment.status = event.status.lower()
        payment.failure_code = event.failure_code
        payment.failure_reason = event.failure_reason
        payment.latency_ms = event.latency_ms
        payment.event_id = event.event_id

        db.commit()
        db.refresh(payment)

        recovery_event = dispatch_recovery_event(
            db=db,
            payment=payment,
            event_id=event.event_id,
        )

        reconciliation = reconcile_recovery_outcome(
            db=db,
            payment_id=payment.payment_id,
            provider_event_id=event.event_id,
            observed_status=payment.status,
        )

        logger.info(
            "hyperswitch.webhook_updated "
            "payment_id=%s event_id=%s status=%s",
            payment.payment_id,
            event.event_id,
            payment.status,
        )

        return {
            "accepted": True,
            "duplicate": False,
            "created": False,
            "payment_id": payment.payment_id,
            "status": payment.status,
            "recovery_event": (
                {
                    "recovery_id": recovery_event.id,
                    "status": recovery_event.status,
                    "action": recovery_event.action,
                    "idempotency_key": recovery_event.idempotency_key,
                }
                if recovery_event
                else None
            ),
            "reconciliation": (
                {
                    "reconciliation_id": reconciliation.reconciliation_id,
                    "status": reconciliation.status,
                    "expected_status": reconciliation.expected_status,
                    "observed_status": reconciliation.observed_status,
                }
                if reconciliation
                else None
            ),
        }

    if event.amount is None:
        return {
            "accepted": False,
            "duplicate": False,
            "created": False,
            "payment_id": event.payment_id,
            "status": event.status.lower(),
            "message": (
                "Amount is required when creating a payment "
                "from a webhook."
            ),
        }

    payment = Payment(
        payment_id=event.payment_id,
        event_id=event.event_id,
        amount=event.amount,
        currency=(
            event.currency.upper()
            if event.currency
            else "INR"
        ),
        method=event.method or "unknown",
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
        "hyperswitch.webhook_created "
        "payment_id=%s event_id=%s status=%s",
        payment.payment_id,
        event.event_id,
        payment.status,
    )

    return {
        "accepted": True,
        "duplicate": False,
        "created": True,
        "payment_id": payment.payment_id,
        "status": payment.status,
    }
