from typing import Any

from app.models.payment import Payment


def build_payment_evidence(
    *,
    payment: Payment,
    incident: dict[str, Any],
) -> dict[str, Any]:
    """Build a normalized, AI-safe evidence payload from payment signals."""

    return {
        "payment": {
            "payment_id": payment.payment_id,
            "status": payment.status,
            "failure_code": payment.failure_code,
            "failure_reason": payment.failure_reason,
            "amount": float(payment.amount),
            "currency": payment.currency,
            "connector": payment.connector,
            "latency_ms": float(payment.latency_ms or 0),
        },
        "incident": {
            "incident": incident.get("incident", False),
            "severity": incident.get("severity"),
            "risk_score": incident.get("risk_score", 0.0),
            "revenue_at_risk": incident.get("revenue_at_risk", 0.0),
            "recovery_priority": incident.get("recovery_priority"),
            "root_cause": incident.get("root_cause"),
            "signals": list(incident.get("signals", [])),
            "recommended_action": incident.get("recommended_action"),
        },
    }
