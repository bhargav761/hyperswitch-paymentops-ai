from app.models.payment import Payment
from app.models.recovery import RecoveryExecution
from app.services.recovery_event_service import dispatch_recovery_event


def test_dispatch_recovery_event_persists_planned_recovery(db_session):
    payment = Payment(
        payment_id="evt-payment-1",
        event_id="evt-1",
        amount=1000,
        currency="INR",
        method="card",
        connector="stripe",
        status="failed",
        failure_code="TIMEOUT",
        failure_reason="connector timeout",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    recovery = dispatch_recovery_event(
        db=db_session,
        payment=payment,
        event_id="evt-1",
    )

    assert recovery is not None
    assert recovery.payment_id == "evt-payment-1"
    assert recovery.status == "PLANNED"
    assert recovery.idempotency_key == "recovery-event:evt-1"

    stored = db_session.query(RecoveryExecution).filter_by(
        payment_id="evt-payment-1"
    ).one()

    assert stored.id == recovery.id


def test_dispatch_recovery_event_is_idempotent(db_session):
    payment = Payment(
        payment_id="evt-payment-2",
        event_id="evt-2",
        amount=1000,
        currency="INR",
        method="card",
        connector="stripe",
        status="failed",
        failure_code="NETWORK_ERROR",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    first = dispatch_recovery_event(db_session, payment, "evt-2")
    second = dispatch_recovery_event(db_session, payment, "evt-2")

    assert first.id == second.id
    assert db_session.query(RecoveryExecution).count() == 1


def test_dispatch_recovery_event_ignores_success(db_session):
    payment = Payment(
        payment_id="evt-payment-3",
        event_id="evt-3",
        amount=1000,
        currency="INR",
        method="card",
        status="succeeded",
    )
    db_session.add(payment)
    db_session.commit()
    db_session.refresh(payment)

    recovery = dispatch_recovery_event(db_session, payment, "evt-3")

    assert recovery is None
    assert db_session.query(RecoveryExecution).count() == 0
