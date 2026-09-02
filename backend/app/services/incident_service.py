from decimal import Decimal

from app.models.payment import Payment
from app.risk.anomaly_detection import detect_payment_anomaly
from app.risk.revenue_risk import calculate_revenue_at_risk
from app.risk.scoring import (
    recovery_priority,
    severity_from_score,
)
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def analyze_payment(payment: Payment) -> dict:
    anomaly = detect_payment_anomaly(
        status=payment.status,
        failure_code=payment.failure_code,
        latency_ms=payment.latency_ms,
    )

    revenue_at_risk = calculate_revenue_at_risk(
        Decimal(str(payment.amount)),
        payment.status,
        payment.failure_code,
    )

    score = anomaly.score

    if payment.failure_code:
        code = payment.failure_code.upper()

        if "NETWORK" in code:
            root_cause = "payment_network_degradation"
            recommendation = "reroute_or_retry"
        elif "TIMEOUT" in code:
            root_cause = "payment_timeout"
            recommendation = "retry_with_backoff"
        elif "ISSUER" in code or "DECLINE" in code:
            root_cause = "issuer_decline"
            recommendation = "alternative_payment_method"
        else:
            root_cause = "connector_or_payment_failure"
            recommendation = "diagnose_before_retry"

    elif payment.status == "pending":
        root_cause = "payment_pending"
        recommendation = "verify_payment_state"

    else:
        root_cause = "no_known_failure"
        recommendation = "no_action"

    severity = severity_from_score(score)

    priority = recovery_priority(
        score,
        float(revenue_at_risk),
    )

    result = {
        "payment_id": payment.payment_id,
        "incident": anomaly.is_anomaly,
        "severity": severity,
        "risk_score": score,
        "revenue_at_risk": float(revenue_at_risk),
        "recovery_priority": priority,
        "root_cause": root_cause,
        "signals": anomaly.signals,
        "recommended_action": recommendation,
    }

    logger.warning(
        "incident.detected payment_id=%s severity=%s "
        "root_cause=%s risk_score=%s revenue_at_risk=%s",
        payment.payment_id,
        severity,
        root_cause,
        score,
        revenue_at_risk,
    )

    return result
