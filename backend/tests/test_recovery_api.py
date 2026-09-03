from fastapi.testclient import TestClient

from app.database.connection import SessionLocal
from app.main import app
from app.models.payment import Payment


client = TestClient(app)


def create_payment(
    payment_id: str,
    event_id: str,
    amount: float,
    status: str = "failed",
    failure_code: str | None = "NETWORK_ERROR",
):
    db = SessionLocal()

    try:
        existing = (
            db.query(Payment)
            .filter(Payment.payment_id == payment_id)
            .first()
        )

        if existing:
            return

        payment = Payment(
            payment_id=payment_id,
            event_id=event_id,
            amount=amount,
            currency="INR",
            method="upi",
            connector="razorpay",
            region="IN",
            status=status,
            failure_code=failure_code,
            failure_reason="Test recovery failure",
            latency_ms=3200,
        )

        db.add(payment)
        db.commit()
    finally:
        db.close()


def test_recovery_plan_contains_p35_orchestration():
    payment_id = "p35_api_network_001"

    create_payment(
        payment_id=payment_id,
        event_id="evt_p35_api_network_001",
        amount=4999,
    )

    response = client.get(
        f"/api/v1/recovery/plan/{payment_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["payment_id"] == payment_id

    assert "incident" in body
    assert "decision" in body
    assert "execution" in body
    assert "next_best_action" in body
    assert "policy" in body
    assert "audit" in body

    assert body["next_best_action"]["action"] == "HUMAN_REVIEW"

    assert body["policy"]["decision"] == "APPROVAL_REQUIRED"
    assert body["policy"]["allowed"] is False

    assert body["execution"]["executed"] is False
    assert body["execution"]["status"] == "approval_required"

    assert body["audit"]["status"] == "approval_required"


def test_recovery_plan_returns_404_for_unknown_payment():
    response = client.get(
        "/api/v1/recovery/plan/p35_payment_does_not_exist"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Payment not found"


def test_recovery_execute_creates_pending_approval():
    payment_id = "p45_api_approval_001"

    create_payment(
        payment_id=payment_id,
        event_id="evt_p45_api_approval_001",
        amount=4999,
    )

    response = client.post(
        f"/api/v1/recovery/execute/{payment_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["policy"]["decision"] == "APPROVAL_REQUIRED"
    assert body["execution"]["executed"] is False
    assert body["execution"]["status"] == "approval_required"

    assert body["approval"] is not None
    assert body["approval"]["payment_id"] == payment_id
    assert body["approval"]["action"] == "HUMAN_REVIEW"
    assert body["approval"]["status"] == "PENDING"


def test_recovery_execute_audits_ai_explanation():
    payment_id = "p56_api_ai_audit_001"

    create_payment(
        payment_id=payment_id,
        event_id="evt_p56_api_ai_audit_001",
        amount=4999,
    )

    response = client.post(
        f"/api/v1/recovery/execute/{payment_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert "ai_analysis" in body
    assert "diagnosis" in body["ai_analysis"]
    assert "recovery_prediction" in body["ai_analysis"]
    assert "recommendation" in body["ai_analysis"]
    assert "routing" in body["ai_analysis"]

    db = SessionLocal()
    try:
        audit = (
            db.query(__import__("app.models.audit", fromlist=["RecoveryAudit"]).RecoveryAudit)
            .filter(
                __import__("app.models.audit", fromlist=["RecoveryAudit"]).RecoveryAudit.payment_id
                == payment_id
            )
            .first()
        )

        assert audit is not None

        import json
        result = json.loads(audit.result)

        assert "ai" in result
        assert "diagnosis" in result["ai"]
        assert "recovery_prediction" in result["ai"]
        assert "recommendation" in result["ai"]
        assert "routing" in result["ai"]
        assert "evidence" in result["ai"]
    finally:
        db.close()
