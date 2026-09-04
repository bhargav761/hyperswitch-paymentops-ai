from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_readiness_endpoint():
    response = client.get("/ready")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "ready"
    assert body["database"] == "up"


def test_metrics_endpoint():
    response = client.get("/metrics")

    assert response.status_code == 200

    body = response.json()

    assert "counters" in body
    assert "circuits" in body
