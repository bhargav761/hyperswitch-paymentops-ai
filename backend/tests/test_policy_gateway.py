from app.recovery.policy_gateway import evaluate_policy_gate


def test_retry_is_allowed_when_policy_is_satisfied():
    result = evaluate_policy_gate(
        payment_id="pay_001",
        amount=5000,
        action="RETRY_LATER",
        confidence=0.82,
        retry_count=0,
    )

    assert result.decision == "ALLOW"
    assert result.allowed is True
    assert result.requires_approval is False
    assert result.idempotency_key == "recovery:pay_001:RETRY_LATER"


def test_retry_is_denied_after_retry_limit():
    result = evaluate_policy_gate(
        payment_id="pay_002",
        amount=5000,
        action="RETRY_NOW",
        confidence=0.90,
        retry_count=2,
    )

    assert result.decision == "DENY"
    assert result.allowed is False
    assert "RETRY_POLICY_BLOCKED" in result.reason_codes


def test_retry_is_denied_when_confidence_is_too_low():
    result = evaluate_policy_gate(
        payment_id="pay_003",
        amount=5000,
        action="RETRY_LATER",
        confidence=0.50,
        retry_count=0,
    )

    assert result.decision == "DENY"
    assert result.allowed is False


def test_retry_is_denied_for_amount_above_policy_limit():
    result = evaluate_policy_gate(
        payment_id="pay_004",
        amount=100001,
        action="RETRY_NOW",
        confidence=0.95,
        retry_count=0,
    )

    assert result.decision == "DENY"
    assert result.allowed is False


def test_human_review_requires_approval():
    result = evaluate_policy_gate(
        payment_id="pay_005",
        amount=5000,
        action="HUMAN_REVIEW",
        confidence=0.50,
    )

    assert result.decision == "APPROVAL_REQUIRED"
    assert result.requires_approval is True
    assert result.allowed is False


def test_reconcile_is_allowed():
    result = evaluate_policy_gate(
        payment_id="pay_006",
        amount=5000,
        action="RECONCILE",
        confidence=0.90,
    )

    assert result.decision == "ALLOW"
    assert result.allowed is True


def test_unknown_action_is_denied():
    result = evaluate_policy_gate(
        payment_id="pay_007",
        amount=5000,
        action="UNKNOWN",
        confidence=0.99,
    )

    assert result.decision == "DENY"
    assert result.allowed is False

def test_policy_gateway_blocks_retry_below_policy_confidence():
    result = evaluate_policy_gate(
        payment_id="pay_safety_001",
        amount=1000,
        action="RETRY_NOW",
        confidence=0.69,
        retry_count=0,
    )

    assert result.decision == "DENY"
    assert result.allowed is False
    assert "RETRY_POLICY_BLOCKED" in result.reason_codes
