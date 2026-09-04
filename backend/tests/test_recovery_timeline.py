import json

from app.models.timeline import RecoveryTimelineEvent
from app.services.recovery_timeline_service import (
    append_recovery_timeline_event,
    get_recovery_timeline,
)


def test_timeline_event_persists(db_session):
    event = append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-001",
        event_type="INCIDENT_DETECTED",
        payload={
            "root_cause": "payment_network_degradation",
            "risk_score": 0.7,
        },
        correlation_key="evt-timeline-001",
        status="PLANNED",
    )

    assert event.id is not None
    assert event.payment_id == "pay-timeline-001"
    assert event.event_type == "INCIDENT_DETECTED"
    assert event.status == "PLANNED"

    payload = json.loads(event.payload)
    assert payload["root_cause"] == "payment_network_degradation"


def test_timeline_preserves_recovery_reference(db_session):
    event = append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-002",
        event_type="EXECUTION",
        payload={"action": "RETRY_NOW"},
        recovery_id=42,
        correlation_key="recovery:42",
        status="EXECUTING",
    )

    assert event.recovery_id == 42
    assert event.correlation_key == "recovery:42"


def test_timeline_returns_events_in_creation_order(db_session):
    append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-003",
        event_type="INCIDENT",
        payload={"step": 1},
    )
    append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-003",
        event_type="DECISION",
        payload={"step": 2},
    )
    append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-003",
        event_type="OUTCOME",
        payload={"step": 3},
    )

    timeline = get_recovery_timeline(
        db_session,
        payment_id="pay-timeline-003",
    )

    assert [event.event_type for event in timeline] == [
        "INCIDENT",
        "DECISION",
        "OUTCOME",
    ]


def test_timeline_is_scoped_to_payment(db_session):
    append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-a",
        event_type="INCIDENT",
        payload={},
    )
    append_recovery_timeline_event(
        db_session,
        payment_id="pay-timeline-b",
        event_type="INCIDENT",
        payload={},
    )

    timeline = get_recovery_timeline(
        db_session,
        payment_id="pay-timeline-a",
    )

    assert len(timeline) == 1
    assert timeline[0].payment_id == "pay-timeline-a"


def test_timeline_model_is_registered():
    assert "recovery_timeline_events" in RecoveryTimelineEvent.metadata.tables
