from decimal import Decimal

from fastapi.testclient import TestClient

from app.database.connection import get_db
from app.llm.gateway import LLMGateway
from app.main import app
from app.models.payment import Payment
from app.api.ai_chat import get_llm_gateway


def _payment(payment_id: str) -> Payment:
    return Payment(
        payment_id=payment_id,
        event_id=f"event-{payment_id}",
        amount=Decimal("300000.00"),
        currency="INR",
        method="upi",
        connector="connector_a",
        region="IN",
        status="failed",
        failure_code="NETWORK_ERROR",
        failure_reason="connector degradation",
        latency_ms=3500,
    )


class FakeQuery:
    def __init__(self, payment):
        self.payment = payment

    def filter(self, *args):
        return self

    def first(self):
        return self.payment


class FakeDB:
    def __init__(self, payment):
        self.payment = payment

    def query(self, model):
        return FakeQuery(self.payment)


class FakeGateway(LLMGateway):
    def __init__(self):
        pass

    def generate(self, *, prompt, context=None):
        assert "PaymentOps recovery guidance" in prompt
        assert context is not None
        assert context["payment"]["payment_id"] == "chat-api"
        return "Recommend advisory retry or reroute based on the grounded evidence."


def test_ai_chat_returns_grounded_advisory_response():
    payment = _payment("chat-api")

    def override_db():
        yield FakeDB(payment)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_llm_gateway] = lambda: FakeGateway()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/ai/chat",
            json={
                "payment_id": "chat-api",
                "message": "What should we recommend for this payment?",
            },
        )

        assert response.status_code == 200
        body = response.json()

        assert body["payment_id"] == "chat-api"
        assert body["advisory_only"] is True
        assert body["grounded"] is True
        assert "retry or reroute" in body["response"]
    finally:
        app.dependency_overrides.clear()


def test_ai_chat_returns_404_for_unknown_payment():
    def override_db():
        yield FakeDB(None)

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_llm_gateway] = lambda: FakeGateway()

    try:
        client = TestClient(app)

        response = client.post(
            "/api/v1/ai/chat",
            json={
                "payment_id": "missing-payment",
                "message": "Analyze this payment.",
            },
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Payment not found."
    finally:
        app.dependency_overrides.clear()
