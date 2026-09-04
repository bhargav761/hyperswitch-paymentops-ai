import json

from sqlalchemy.orm import Session

from app.models.timeline import RecoveryTimelineEvent


def append_recovery_timeline_event(
    db: Session,
    *,
    payment_id: str,
    event_type: str,
    payload: dict,
    recovery_id: int | None = None,
    correlation_key: str | None = None,
    status: str | None = None,
) -> RecoveryTimelineEvent:
    event = RecoveryTimelineEvent(
        payment_id=payment_id,
        event_type=event_type,
        recovery_id=recovery_id,
        correlation_key=correlation_key,
        status=status,
        payload=json.dumps(payload),
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


def get_recovery_timeline(
    db: Session,
    *,
    payment_id: str,
) -> list[RecoveryTimelineEvent]:
    return (
        db.query(RecoveryTimelineEvent)
        .filter(RecoveryTimelineEvent.payment_id == payment_id)
        .order_by(
            RecoveryTimelineEvent.created_at.asc(),
            RecoveryTimelineEvent.id.asc(),
        )
        .all()
    )
