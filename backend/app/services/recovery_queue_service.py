import json

from sqlalchemy.orm import Session

from app.services.recovery_timeline_service import append_recovery_timeline_event

from app.models.recovery_queue import RecoveryQueueItem


def enqueue_recovery(
    db: Session,
    *,
    payment_id: str,
    action: str,
    idempotency_key: str,
    payload: dict,
    max_attempts: int = 3,
) -> tuple[RecoveryQueueItem, bool]:
    existing = (
        db.query(RecoveryQueueItem)
        .filter(
            RecoveryQueueItem.idempotency_key == idempotency_key
        )
        .first()
    )

    if existing:
        return existing, False

    item = RecoveryQueueItem(
        payment_id=payment_id,
        action=action,
        idempotency_key=idempotency_key,
        status="QUEUED",
        attempt_count=0,
        max_attempts=max_attempts,
        payload=json.dumps(payload),
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return item, True


def claim_next_recovery(
    db: Session,
) -> RecoveryQueueItem | None:
    item = (
        db.query(RecoveryQueueItem)
        .filter(
            RecoveryQueueItem.status == "QUEUED",
            RecoveryQueueItem.attempt_count
            < RecoveryQueueItem.max_attempts,
        )
        .order_by(
            RecoveryQueueItem.created_at.asc(),
            RecoveryQueueItem.id.asc(),
        )
        .first()
    )

    if not item:
        return None

    item.status = "PROCESSING"
    item.attempt_count = int(item.attempt_count or 0) + 1

    db.add(item)
    db.commit()
    db.refresh(item)

    append_recovery_timeline_event(
        db,
        payment_id=item.payment_id,
        event_type="RECOVERY_QUEUE_PROCESSING",
        recovery_id=item.id,
        correlation_key=item.idempotency_key,
        status=item.status,
        payload={
            "action": item.action,
            "attempt_count": item.attempt_count,
            "max_attempts": item.max_attempts,
        },
    )

    return item


def complete_recovery(
    db: Session,
    *,
    queue_id: int,
    success: bool,
    error: str | None = None,
) -> RecoveryQueueItem:
    item = (
        db.query(RecoveryQueueItem)
        .filter(RecoveryQueueItem.id == queue_id)
        .first()
    )

    if not item:
        raise ValueError(f"Recovery queue item {queue_id} not found")

    if success:
        item.status = "COMPLETED"
        item.error = None
    elif item.attempt_count >= item.max_attempts:
        item.status = "DEAD_LETTER"
        item.error = error
    else:
        item.status = "QUEUED"
        item.error = error

    db.add(item)
    db.commit()
    db.refresh(item)

    if success:
        event_type = "RECOVERY_QUEUE_COMPLETED"
    elif item.status == "DEAD_LETTER":
        event_type = "RECOVERY_QUEUE_DEAD_LETTER"
    else:
        event_type = "RECOVERY_QUEUE_REQUEUED"

    append_recovery_timeline_event(
        db,
        payment_id=item.payment_id,
        event_type=event_type,
        recovery_id=item.id,
        correlation_key=item.idempotency_key,
        status=item.status,
        payload={
            "action": item.action,
            "attempt_count": item.attempt_count,
            "max_attempts": item.max_attempts,
            "error": error,
        },
    )

    return item


def get_queue_item(
    db: Session,
    *,
    queue_id: int,
) -> RecoveryQueueItem | None:
    return (
        db.query(RecoveryQueueItem)
        .filter(RecoveryQueueItem.id == queue_id)
        .first()
    )
