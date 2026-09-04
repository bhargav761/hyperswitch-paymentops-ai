from app.models.recovery import RecoveryExecution
from app.services.recovery_idempotency_service import claim_recovery


def test_claim_recovery_creates_once(db_session):
    first, created = claim_recovery(
        db_session,
        payment_id="idem-1",
        action="RETRY_NOW",
        connector="stripe",
        confidence=0.9,
    )

    second, created_again = claim_recovery(
        db_session,
        payment_id="idem-1",
        action="RETRY_NOW",
        connector="stripe",
        confidence=0.9,
    )

    assert created is True
    assert created_again is False
    assert first.id == second.id
    assert first.idempotency_key == "recovery:idem-1:RETRY_NOW"
    assert db_session.query(RecoveryExecution).count() == 1


def test_claim_recovery_allows_different_actions(db_session):
    retry, retry_created = claim_recovery(
        db_session,
        payment_id="idem-2",
        action="RETRY_NOW",
    )

    reconcile, reconcile_created = claim_recovery(
        db_session,
        payment_id="idem-2",
        action="RECONCILE",
    )

    assert retry_created is True
    assert reconcile_created is True
    assert retry.id != reconcile.id
    assert db_session.query(RecoveryExecution).count() == 2
