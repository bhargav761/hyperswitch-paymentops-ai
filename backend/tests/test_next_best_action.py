from app.recovery.next_best_action import build_next_best_action


def test_timeout_recommends_delayed_retry():
    result = build_next_best_action(
        recovery_action="retry_with_backoff",
        confidence=0.82,
        reason="Payment timeout detected",
        requires_approval=False,
        root_cause="payment_timeout",
        risk_score=0.20,
    )

    assert result.action == "RETRY_LATER"
    assert result.confidence == 0.82
    assert result.delay_seconds == 1800
    assert result.requires_approval is False
    assert "PAYMENT_TIMEOUT" in result.reason_codes


def test_network_degradation_recommends_retry():
    result = build_next_best_action(
        recovery_action="reroute_or_retry",
        confidence=0.85,
        reason="Network degradation detected",
        requires_approval=False,
        root_cause="payment_network_degradation",
        risk_score=0.20,
    )

    assert result.action == "RETRY_NOW"
    assert result.delay_seconds is None


def test_pending_payment_recommends_reconciliation():
    result = build_next_best_action(
        recovery_action="verify_payment_state",
        confidence=0.90,
        reason="Payment is pending",
        requires_approval=False,
        root_cause="payment_pending",
        risk_score=0.10,
    )

    assert result.action == "RECONCILE"
    assert result.requires_approval is False


def test_issuer_decline_recommends_alternative_payment():
    result = build_next_best_action(
        recovery_action="alternative_payment_method",
        confidence=0.88,
        reason="Issuer decline detected",
        requires_approval=False,
        root_cause="issuer_decline",
        risk_score=0.15,
    )

    assert result.action == "ALTERNATIVE_PAYMENT"


def test_high_risk_blocks_automatic_retry():
    result = build_next_best_action(
        recovery_action="retry_with_backoff",
        confidence=0.90,
        reason="Retry recommended",
        requires_approval=False,
        root_cause="payment_timeout",
        risk_score=0.90,
    )

    assert result.action == "HUMAN_REVIEW"
    assert result.requires_approval is True
    assert result.delay_seconds is None
    assert "HIGH_RISK" in result.reason_codes


def test_unknown_action_falls_back_to_human_review():
    result = build_next_best_action(
        recovery_action="something_unknown",
        confidence=0.50,
        reason="Unknown condition",
        requires_approval=True,
        root_cause="unknown",
        risk_score=0.40,
    )

    assert result.action == "HUMAN_REVIEW"
    assert result.requires_approval is True
