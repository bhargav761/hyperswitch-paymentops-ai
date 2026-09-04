import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

import httpx
import pytest

from app.models.recovery import RecoveryExecution
from app.services.recovery_event_service import dispatch_recovery_event
from app.services.recovery_idempotency_service import claim_recovery
from app.services.recovery_outcome_service import record_recovery_outcome
from app.services.recovery_state_machine import InvalidRecoveryTransition
from app.services.recovery_execution_service import execute_policy_approved_recovery


def _payment(status="failed"):
    return SimpleNamespace(
        payment_id="pay_phase7_resilience",
        status=status,
        failure_code="NETWORK_ERROR",
        failure_reason="temporary network failure",
        amount=100.0,
        currency="INR",
        method="card",
        connector="stripe",
        latency_ms=400,
    )


def _policy(action="RETRY_NOW"):
    return SimpleNamespace(
        decision="ALLOW",
        allowed=True,
        requires_approval=False,
        action=action,
        idempotency_key=f"recovery:pay_phase7_resilience:{action}",
    )


def test_duplicate_event_is_idempotent(db_session):
    payment = _payment()

    first = dispatch_recovery_event(
        db_session,
        payment,
        "evt-phase7-001",
    )
    second = dispatch_recovery_event(
        db_session,
        payment,
        "evt-phase7-001",
    )

    assert first is not None
    assert second is not None
    assert first.id == second.id

    count = (
        db_session.query(RecoveryExecution)
        .filter(
            RecoveryExecution.idempotency_key
            == "recovery-event:evt-phase7-001"
        )
        .count()
    )
    assert count == 1


def test_concurrent_style_duplicate_claim_is_idempotent(db_session):
    first, created = claim_recovery(
        db_session,
        payment_id="pay-concurrent",
        action="RETRY_NOW",
    )
    second, created_again = claim_recovery(
        db_session,
        payment_id="pay-concurrent",
        action="RETRY_NOW",
    )

    assert created is True
    assert created_again is False
    assert first.id == second.id


def test_provider_timeout_is_safe():
    adapter = Mock()
    adapter.execute_retry.side_effect = httpx.TimeoutException("timeout")

    result = execute_policy_approved_recovery(
        policy=_policy(),
        payment_id="pay-timeout",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=adapter,
    )

    assert result["executed"] is False
    assert result["success"] is False
    assert result["status"] == "provider_timeout"


def test_provider_http_failure_is_safe():
    adapter = Mock()
    response = httpx.Response(503)
    adapter.execute_retry.side_effect = httpx.HTTPStatusError(
        "service unavailable",
        request=httpx.Request("POST", "http://provider"),
        response=response,
    )

    result = execute_policy_approved_recovery(
        policy=_policy(),
        payment_id="pay-http-error",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=adapter,
    )

    assert result["executed"] is False
    assert result["success"] is False
    assert result["status"] == "provider_error"
    assert result["error_code"] == "PROVIDER_HTTP_503"


def test_provider_unavailable_is_safe():
    adapter = Mock()
    adapter.execute_retry.side_effect = httpx.ConnectError("unavailable")

    result = execute_policy_approved_recovery(
        policy=_policy(),
        payment_id="pay-unavailable",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=adapter,
    )

    assert result["executed"] is False
    assert result["success"] is False
    assert result["status"] == "provider_unavailable"


def test_invalid_terminal_transition_is_rejected(db_session):
    execution = RecoveryExecution(
        payment_id="pay-terminal",
        idempotency_key="terminal:test",
        action="RETRY_NOW",
        status="SUCCEEDED",
        attempt_count=0,
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)

    with pytest.raises(InvalidRecoveryTransition):
        record_recovery_outcome(
            db_session,
            execution_id=execution.id,
            outcome={
                "status": "failed",
                "success": False,
            },
        )


def test_policy_denial_never_reaches_provider():
    adapter = Mock()
    policy = SimpleNamespace(
        decision="DENY",
        allowed=False,
        requires_approval=False,
        action="RETRY_NOW",
        idempotency_key="recovery:denied",
    )

    result = execute_policy_approved_recovery(
        policy=policy,
        payment_id="pay-denied",
        amount=100.0,
        currency="INR",
        payment_method="card",
        connector="stripe",
        adapter=adapter,
    )

    assert result["executed"] is False
    assert result["status"] == "blocked"
    adapter.execute_retry.assert_not_called()


def test_recovery_outcome_preserves_provider_details(db_session):
    execution = RecoveryExecution(
        payment_id="pay-feedback",
        idempotency_key="feedback:test",
        action="RETRY_NOW",
        status="EXECUTING",
        attempt_count=0,
    )
    db_session.add(execution)
    db_session.commit()
    db_session.refresh(execution)

    result = record_recovery_outcome(
        db_session,
        execution_id=execution.id,
        outcome={
            "status": "succeeded",
            "success": True,
            "provider_reference": "provider-ref-77",
        },
    )

    payload = json.loads(result.result)
    assert result.status == "SUCCEEDED"
    assert payload["outcome"]["provider_reference"] == "provider-ref-77"
