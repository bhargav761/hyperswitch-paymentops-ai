from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_operations_feedback_endpoint():
    response = client.get("/api/v1/operations/feedback")

    assert response.status_code == 200
    body = response.json()
    assert "total_executions" in body
    assert "success_rate" in body


def test_operations_circuits_endpoint():
    response = client.get("/api/v1/operations/circuits")

    assert response.status_code == 200
    assert "circuits" in response.json()


def test_operations_metrics_endpoint():
    response = client.get("/api/v1/operations/metrics")

    assert response.status_code == 200
    body = response.json()
    assert "counters" in body
    assert "circuits" in body


def test_recovery_status_not_found():
    response = client.get("/api/v1/operations/recoveries/nonexistent-payment")

    assert response.status_code == 404


def test_recovery_audits_empty_for_unknown_payment():
    response = client.get("/api/v1/operations/audits/nonexistent-payment")

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 0
    assert body["audits"] == []


def test_recovery_timeline_endpoint():
    response = client.get("/api/v1/operations/timeline/nonexistent-payment")

    assert response.status_code == 200
    body = response.json()
    assert body["payment_id"] == "nonexistent-payment"
    assert body["count"] == 0
    assert body["timeline"] == []
