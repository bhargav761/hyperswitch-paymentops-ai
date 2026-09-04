from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.services.recovery_queue_service import get_queue_item
from app.services.recovery_worker import process_next_recovery
from app.models.recovery_queue import RecoveryQueueItem
from app.config.settings import (
    HYPERSWITCH_API_KEY,
    HYPERSWITCH_BASE_URL,
    HYPERSWITCH_TIMEOUT_SECONDS,
)

router = APIRouter(prefix="/api/v1/operations/queue", tags=["recovery-queue"])


@router.get("")
def list_recovery_queue(
    status: str | None = Query(default=None, min_length=1, max_length=50),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(RecoveryQueueItem)

    if status:
        query = query.filter(RecoveryQueueItem.status == status)

    items = (
        query
        .order_by(RecoveryQueueItem.created_at.asc(), RecoveryQueueItem.id.asc())
        .limit(limit)
        .all()
    )

    return {
        "count": len(items),
        "items": [
            {
                "id": item.id,
                "payment_id": item.payment_id,
                "idempotency_key": item.idempotency_key,
                "action": item.action,
                "status": item.status,
                "attempt_count": item.attempt_count,
                "max_attempts": item.max_attempts,
                "error": item.error,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            for item in items
        ],
    }


@router.get("/{queue_id}")
def recovery_queue_item(
    queue_id: int,
    db: Session = Depends(get_db),
):
    item = get_queue_item(db, queue_id=queue_id)

    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    return {
        "id": item.id,
        "payment_id": item.payment_id,
        "idempotency_key": item.idempotency_key,
        "action": item.action,
        "status": item.status,
        "attempt_count": item.attempt_count,
        "max_attempts": item.max_attempts,
        "payload": item.payload,
        "error": item.error,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.post("/worker/run")
def run_recovery_worker(
    db: Session = Depends(get_db),
):
    item = process_next_recovery(
        db,
        hyperswitch_base_url=HYPERSWITCH_BASE_URL,
        hyperswitch_api_key=HYPERSWITCH_API_KEY,
        hyperswitch_timeout_seconds=HYPERSWITCH_TIMEOUT_SECONDS,
    )

    if not item:
        return {
            "processed": False,
            "message": "No queued recovery available",
        }

    return {
        "processed": True,
        "queue_id": item.id,
        "payment_id": item.payment_id,
        "status": item.status,
        "attempt_count": item.attempt_count,
    }
