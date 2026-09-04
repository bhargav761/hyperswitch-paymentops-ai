import json

from app.models.recovery_queue import RecoveryQueueItem
from app.services.recovery_queue_service import (
    claim_next_recovery,
    complete_recovery,
    enqueue_recovery,
    get_queue_item,
)


def test_enqueue_recovery_is_idempotent(db_session):
    first, created = enqueue_recovery(
        db_session,
        payment_id="pay-queue-001",
        action="RETRY_NOW",
        idempotency_key="queue:event-001",
        payload={"event_id": "event-001"},
    )

    second, created_again = enqueue_recovery(
        db_session,
        payment_id="pay-queue-001",
        action="RETRY_NOW",
        idempotency_key="queue:event-001",
        payload={"event_id": "event-001"},
    )

    assert created is True
    assert created_again is False
    assert first.id == second.id


def test_claim_moves_item_to_processing(db_session):
    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-queue-002",
        action="RETRY_NOW",
        idempotency_key="queue:event-002",
        payload={"event_id": "event-002"},
    )

    claimed = claim_next_recovery(db_session)

    assert claimed is not None
    assert claimed.id == item.id
    assert claimed.status == "PROCESSING"
    assert claimed.attempt_count == 1


def test_successful_completion_is_terminal(db_session):
    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-queue-003",
        action="RETRY_NOW",
        idempotency_key="queue:event-003",
        payload={"event_id": "event-003"},
    )
    claim_next_recovery(db_session)

    completed = complete_recovery(
        db_session,
        queue_id=item.id,
        success=True,
    )

    assert completed.status == "COMPLETED"
    assert completed.error is None


def test_failed_item_is_requeued_before_limit(db_session):
    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-queue-004",
        action="RETRY_NOW",
        idempotency_key="queue:event-004",
        payload={"event_id": "event-004"},
        max_attempts=3,
    )
    claim_next_recovery(db_session)

    failed = complete_recovery(
        db_session,
        queue_id=item.id,
        success=False,
        error="temporary provider failure",
    )

    assert failed.status == "QUEUED"
    assert failed.error == "temporary provider failure"
    assert failed.attempt_count == 1


def test_failed_item_becomes_dead_letter_at_limit(db_session):
    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-queue-005",
        action="RETRY_NOW",
        idempotency_key="queue:event-005",
        payload={"event_id": "event-005"},
        max_attempts=1,
    )
    claim_next_recovery(db_session)

    failed = complete_recovery(
        db_session,
        queue_id=item.id,
        success=False,
        error="permanent failure",
    )

    assert failed.status == "DEAD_LETTER"
    assert failed.error == "permanent failure"


def test_queue_claim_respects_attempt_limit(db_session):
    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-queue-006",
        action="RETRY_NOW",
        idempotency_key="queue:event-006",
        payload={"event_id": "event-006"},
        max_attempts=1,
    )
    claim_next_recovery(db_session)
    complete_recovery(
        db_session,
        queue_id=item.id,
        success=False,
        error="failure",
    )

    assert claim_next_recovery(db_session) is None


def test_queue_payload_is_persisted(db_session):
    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-queue-007",
        action="RECONCILE",
        idempotency_key="queue:event-007",
        payload={"event_id": "event-007", "priority": "HIGH"},
    )

    stored = get_queue_item(
        db_session,
        queue_id=item.id,
    )

    assert stored is not None
    assert json.loads(stored.payload)["priority"] == "HIGH"


def test_queue_model_registered():
    assert "recovery_queue_items" in RecoveryQueueItem.metadata.tables


def test_queue_lifecycle_emits_timeline_events(db_session):
    from app.services.recovery_queue_service import (
        enqueue_recovery,
        claim_next_recovery,
        complete_recovery,
    )
    from app.services.recovery_timeline_service import get_recovery_timeline

    item, _ = enqueue_recovery(
        db_session,
        payment_id="pay-lifecycle-001",
        idempotency_key="recovery:pay-lifecycle-001:RETRY_NOW",
        action="RETRY_NOW",
        payload={"source": "phase8"},
    )

    claimed = claim_next_recovery(db_session)
    assert claimed.id == item.id

    complete_recovery(
        db_session,
        queue_id=item.id,
        success=True,
    )

    events = get_recovery_timeline(
        db_session,
        payment_id="pay-lifecycle-001",
    )

    event_types = [event.event_type for event in events]

    assert "RECOVERY_QUEUE_PROCESSING" in event_types
    assert "RECOVERY_QUEUE_COMPLETED" in event_types
    assert all(event.recovery_id == item.id for event in events)
    assert all(event.correlation_key == item.idempotency_key for event in events)
