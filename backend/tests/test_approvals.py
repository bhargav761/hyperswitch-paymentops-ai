from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import SessionLocal, engine
from app.models.approval import RecoveryApproval
from app.models.payment import Base

Base.metadata.create_all(bind=engine)

client = TestClient(app)


def cleanup(payment_id: str):
    db = SessionLocal()
    try:
        db.query(RecoveryApproval).filter(
            RecoveryApproval.payment_id == payment_id
        ).delete()
        db.commit()
    finally:
        db.close()


def test_create_approval_is_idempotent():
    payment_id = "approval_test_create"

    try:
        first = client.post(
            f"/api/v1/approvals/{payment_id}/request",
            params={
                "action": "HUMAN_REVIEW",
                "reason": "High risk recovery requires review",
                "confidence": 0.91,
            },
        )
        second = client.post(
            f"/api/v1/approvals/{payment_id}/request",
            params={
                "action": "HUMAN_REVIEW",
                "reason": "High risk recovery requires review",
                "confidence": 0.91,
            },
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["approval_id"] == second.json()["approval_id"]
        assert first.json()["status"] == "PENDING"

    finally:
        cleanup(payment_id)


def test_approval_can_be_approved():
    payment_id = "approval_test_approve"

    try:
        request = client.post(
            f"/api/v1/approvals/{payment_id}/request",
            params={
                "action": "HUMAN_REVIEW",
                "reason": "Manual review required",
                "confidence": 0.88,
            },
        )

        assert request.status_code == 200

        decision = client.post(
            f"/api/v1/approvals/{payment_id}/decide",
            json={
                "approved": True,
                "approved_by": "risk-operator",
            },
        )

        assert decision.status_code == 200
        body = decision.json()
        assert body["status"] == "APPROVED"
        assert body["approved_by"] == "risk-operator"

    finally:
        cleanup(payment_id)


def test_approval_can_be_rejected():
    payment_id = "approval_test_reject"

    try:
        request = client.post(
            f"/api/v1/approvals/{payment_id}/request",
            params={
                "action": "HUMAN_REVIEW",
                "reason": "Risk threshold exceeded",
                "confidence": 0.95,
            },
        )

        assert request.status_code == 200

        decision = client.post(
            f"/api/v1/approvals/{payment_id}/decide",
            json={
                "approved": False,
                "approved_by": "risk-operator",
            },
        )

        assert decision.status_code == 200
        assert decision.json()["status"] == "REJECTED"

    finally:
        cleanup(payment_id)


def test_approval_status_can_be_retrieved():
    payment_id = "approval_test_get"

    try:
        created = client.post(
            f"/api/v1/approvals/{payment_id}/request",
            params={
                "action": "HUMAN_REVIEW",
                "reason": "Operator review",
                "confidence": 0.80,
            },
        )

        approval_id = created.json()["approval_id"]

        response = client.get(
            f"/api/v1/approvals/{payment_id}"
        )

        assert response.status_code == 200
        assert response.json()["approval_id"] == approval_id
        assert response.json()["status"] == "PENDING"

    finally:
        cleanup(payment_id)

def test_approval_request_rejects_invalid_confidence():
    response = client.post(
        "/api/v1/approvals/pay_security_001/request",
        json={
            "action": "RETRY_NOW",
            "reason": "test",
            "confidence": 2.0,
        },
    )

    assert response.status_code == 422


def test_approval_request_rejects_empty_reason():
    response = client.post(
        "/api/v1/approvals/pay_security_002/request",
        json={
            "action": "RETRY_NOW",
            "reason": "",
            "confidence": 0.8,
        },
    )

    assert response.status_code == 422
