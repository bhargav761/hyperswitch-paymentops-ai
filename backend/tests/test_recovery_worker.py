from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.services.recovery_worker import process_next_recovery


def _item(payment_id="pay-worker-001"):
    return SimpleNamespace(
        id=1,
        payment_id=payment_id,
        status="PROCESSING",
        attempt_count=1,
        max_attempts=3,
    )


def _payment(payment_id="pay-worker-001"):
    return SimpleNamespace(
        payment_id=payment_id,
        amount=100.0,
        currency="INR",
        method="card",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="network failure",
        connector="stripe",
        latency_ms=400,
    )


@patch("app.services.recovery_worker.complete_recovery")
@patch("app.services.recovery_worker.orchestrate_recovery")
@patch("app.services.recovery_worker.claim_next_recovery")
def test_worker_processes_successful_recovery(
    claim,
    orchestrator,
    complete,
    db_session,
):
    item = _item()
    payment = _payment()

    claim.return_value = item
    orchestrator.return_value = SimpleNamespace(
        execution={
            "executed": True,
            "success": True,
            "status": "succeeded",
        },
    )

    query = Mock()
    query.filter.return_value.first.return_value = payment
    db_session.query = Mock(return_value=query)

    result = process_next_recovery(
        db_session,
        hyperswitch_base_url="http://localhost",
        hyperswitch_api_key=None,
        hyperswitch_timeout_seconds=1.0,
    )

    assert result is item
    complete.assert_called_once_with(
        db_session,
        queue_id=item.id,
        success=True,
        error=None,
    )
    orchestrator.assert_called_once()


@patch("app.services.recovery_worker.complete_recovery")
@patch("app.services.recovery_worker.orchestrate_recovery")
@patch("app.services.recovery_worker.claim_next_recovery")
def test_worker_requeues_failed_recovery(
    claim,
    orchestrator,
    complete,
    db_session,
):
    item = _item("pay-worker-002")
    payment = _payment("pay-worker-002")

    claim.return_value = item
    orchestrator.return_value = SimpleNamespace(
        execution={
            "executed": False,
            "success": False,
            "status": "provider_timeout",
            "error_message": "timeout",
        },
    )

    query = Mock()
    query.filter.return_value.first.return_value = payment
    db_session.query = Mock(return_value=query)

    result = process_next_recovery(
        db_session,
        hyperswitch_base_url="http://localhost",
        hyperswitch_api_key=None,
        hyperswitch_timeout_seconds=1.0,
    )

    assert result is item
    complete.assert_called_once_with(
        db_session,
        queue_id=item.id,
        success=False,
        error="timeout",
    )


@patch("app.services.recovery_worker.complete_recovery")
@patch("app.services.recovery_worker.claim_next_recovery")
def test_worker_handles_missing_payment(
    claim,
    complete,
    db_session,
):
    item = _item("pay-worker-missing")
    claim.return_value = item

    query = Mock()
    query.filter.return_value.first.return_value = None
    db_session.query = Mock(return_value=query)

    result = process_next_recovery(
        db_session,
        hyperswitch_base_url="http://localhost",
        hyperswitch_api_key=None,
        hyperswitch_timeout_seconds=1.0,
    )

    assert result is item
    complete.assert_called_once_with(
        db_session,
        queue_id=item.id,
        success=False,
        error="Payment not found",
    )
