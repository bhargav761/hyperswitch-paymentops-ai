import json

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import SessionLocal
from app.models.payment import Payment

client = TestClient(app)


def cleanup(payment_id: str):
    db = SessionLocal()
    try:
        payment = (
            db.query(Payment)
            .filter(Payment.payment_id == payment_id)
            .first()
        )
        if payment:
            db.delete(payment)
            db.commit()
    finally:
        db.close()


def test_webhook_creates_payment():
    payment_id = "webhook_pay_create"

    try:
        response = client.post(
            "/api/v1/webhooks/hyperswitch",
            json={
                "event_id": "evt_webhook_create",
                "payment_id": payment_id,
                "status": "failed",
                "amount": 100.50,
                "currency": "inr",
                "method": "card",
                "connector": "stripe",
                "region": "IN",
                "failure_code": "insufficient_funds",
                "failure_reason": "Insufficient funds",
                "latency_ms": 450,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["accepted"] is True
        assert body["created"] is True
        assert body["payment_id"] == payment_id
        assert body["status"] == "failed"

    finally:
        cleanup(payment_id)


def test_webhook_duplicate_is_idempotent():
    payment_id = "webhook_pay_duplicate"

    try:
        payload = {
            "event_id": "evt_webhook_duplicate",
            "payment_id": payment_id,
            "status": "failed",
            "amount": 200,
            "currency": "INR",
            "method": "card",
        }

        first = client.post(
            "/api/v1/webhooks/hyperswitch",
            json=payload,
        )
        second = client.post(
            "/api/v1/webhooks/hyperswitch",
            json=payload,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["created"] is True
        assert second.json()["duplicate"] is True

    finally:
        cleanup(payment_id)


def test_webhook_updates_existing_payment():
    payment_id = "webhook_pay_update"

    try:
        db = SessionLocal()
        payment = Payment(
            payment_id=payment_id,
            event_id="initial_event",
            amount=300,
            currency="INR",
            method="card",
            connector="stripe",
            region="IN",
            status="failed",
        )
        db.add(payment)
        db.commit()
        db.close()

        response = client.post(
            "/api/v1/webhooks/hyperswitch",
            json={
                "event_id": "evt_webhook_update",
                "payment_id": payment_id,
                "status": "succeeded",
                "amount": 300,
                "currency": "INR",
                "method": "card",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["accepted"] is True
        assert body["created"] is False
        assert body["status"] == "succeeded"

    finally:
        cleanup(payment_id)


def test_webhook_requires_amount_for_new_payment():
    payment_id = "webhook_pay_no_amount"

    try:
        response = client.post(
            "/api/v1/webhooks/hyperswitch",
            json={
                "event_id": "evt_webhook_no_amount",
                "payment_id": payment_id,
                "status": "failed",
                "currency": "INR",
                "method": "card",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["accepted"] is False
        assert body["created"] is False

    finally:
        cleanup(payment_id)
