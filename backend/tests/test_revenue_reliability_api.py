from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.database.connection import get_db
from app.models.payment import Payment


def _payment(payment_id, connector="connector_a"):
    return Payment(
        payment_id=payment_id,
        event_id=f"event-{payment_id}",
        amount=Decimal("300000.00"),
        currency="INR",
        method="upi",
        connector=connector,
        region="IN",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="connector degradation",
        latency_ms=3500,
    )


def test_revenue_reliability_analyze_endpoint():
    payments = [
        _payment(f"api-{i}")
        for i in range(5)
    ]

    def override_db():
        class FakeQuery:
            def order_by(self, *args):
                return self

            def all(self):
                return payments

        class FakeDB:
            def query(self, model):
                return FakeQuery()

        yield FakeDB()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/revenue-reliability/analyze"
        )

        assert response.status_code == 200
        body = response.json()
        assert body["incident"]["incident"] is True
        assert body["revenue_decision"]["decision"] == "INTERVENE"
        assert body["revenue_decision"]["target_connector"] == "connector_b"
    finally:
        app.dependency_overrides.clear()


def test_revenue_reliability_verify_endpoint():
    payment = _payment("verify-api")

    def override_db():
        class FakeQuery:
            def filter(self, *args):
                return self

            def first(self):
                return payment

        class FakeDB:
            def query(self, model):
                return FakeQuery()

        yield FakeDB()

    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/revenue-reliability/verify/verify-api",
            params={
                "failure_rate_before": 0.50,
                "failure_rate_after": 0.05,
                "latency_before_ms": 3500,
                "latency_after_ms": 900,
                "revenue_at_risk_before_per_hour": 1500000,
                "revenue_at_risk_after_per_hour": 250000,
                "payments_recovered": 42,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["verification_status"] == "VERIFIED"
        assert body["revenue_protected_per_hour"] == 1250000.0
        assert body["revenue_recovered"] == 1250000.0
        assert body["payments_recovered"] == 42
    finally:
        app.dependency_overrides.clear()
