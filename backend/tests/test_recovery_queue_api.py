from datetime import datetime
from unittest.mock import Mock

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _item(queue_id=1, status="QUEUED"):
    return Mock(
        id=queue_id,
        payment_id="pay-api-001",
        idempotency_key="recovery:pay-api-001:RETRY_NOW",
        action="RETRY_NOW",
        status=status,
        attempt_count=0,
        max_attempts=3,
        payload='{"source":"test"}',
        error=None,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def test_queue_endpoint_is_registered():
    response = client.get("/api/v1/operations/queue")
    assert response.status_code == 200
    assert "count" in response.json()
    assert "items" in response.json()


def test_queue_item_not_found():
    response = client.get("/api/v1/operations/queue/999999")
    assert response.status_code == 404


def test_queue_worker_endpoint_is_registered():
    response = client.post("/api/v1/operations/queue/worker/run")
    assert response.status_code == 200
    assert response.json()["processed"] is False
