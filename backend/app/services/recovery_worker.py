from app.models.payment import Payment
from app.services.recovery_orchestrator import orchestrate_recovery
from app.services.recovery_queue_service import (
    claim_next_recovery,
    complete_recovery,
)


def process_next_recovery(
    db,
    *,
    hyperswitch_base_url: str,
    hyperswitch_api_key: str | None,
    hyperswitch_timeout_seconds: float,
):
    item = claim_next_recovery(db)

    if not item:
        return None

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == item.payment_id)
        .first()
    )

    if not payment:
        complete_recovery(
            db,
            queue_id=item.id,
            success=False,
            error="Payment not found",
        )
        return item

    try:
        result = orchestrate_recovery(
            db=db,
            payment=payment,
            hyperswitch_base_url=hyperswitch_base_url,
            hyperswitch_api_key=hyperswitch_api_key,
            hyperswitch_timeout_seconds=hyperswitch_timeout_seconds,
        )

        success = bool(result.execution.get("success", False))

        complete_recovery(
            db,
            queue_id=item.id,
            success=success,
            error=(
                result.execution.get("error_message")
                if not success
                else None
            ),
        )

        return item

    except Exception as exc:
        complete_recovery(
            db,
            queue_id=item.id,
            success=False,
            error=str(exc),
        )
        return item
