from fastapi import APIRouter

from app.database.connection import engine
from app.observability import metrics
from app.routing.circuit_breaker import circuit_breaker

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "paymentops-ai",
    }


@router.get("/ready")
def readiness():
    try:
        with engine.connect():
            database = "up"
    except Exception:
        database = "down"

    status = "ready" if database == "up" else "not_ready"

    return {
        "status": status,
        "database": database,
    }


@router.get("/metrics")
def get_metrics():
    return {
        "counters": metrics.snapshot(),
        "circuits": circuit_breaker.snapshot(),
    }
