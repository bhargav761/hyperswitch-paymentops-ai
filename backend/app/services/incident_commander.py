from collections import Counter
from decimal import Decimal
from uuid import uuid4

from app.models.payment import Payment
from app.risk.anomaly_detection import detect_payment_anomaly
from app.risk.scoring import severity_from_score
from app.services.logging_service import get_logger
from app.services.revenue_decision_engine import decide_revenue_intervention

logger = get_logger(__name__)


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _dominant(values: list[str | None]) -> str | None:
    normalized = [str(value) for value in values if value]
    if not normalized:
        return None
    return Counter(normalized).most_common(1)[0][0]


def analyze_system_incident(
    payments: list[Payment],
    *,
    window_minutes: int = 60,
) -> dict:
    total = len(payments)

    if total == 0:
        return {
            "incident_id": None,
            "incident": False,
            "severity": "LOW",
            "confidence": 0.0,
            "root_cause": "insufficient_payment_data",
            "revenue_at_risk_per_hour": 0.0,
            "affected_payments": 0,
            "failure_rate": 0.0,
            "average_latency_ms": 0.0,
            "affected_connector": None,
            "affected_method": None,
            "affected_region": None,
            "signals": [],
            "recommended_action": "collect_more_telemetry",
            "window_minutes": window_minutes,
        }

    failures = [
        payment
        for payment in payments
        if str(payment.status).lower() in {"failed", "declined"}
    ]

    latencies = [
        float(payment.latency_ms)
        for payment in payments
        if payment.latency_ms is not None
    ]

    failure_rate = _rate(len(failures), total)
    average_latency = (
        round(sum(latencies) / len(latencies), 2)
        if latencies
        else 0.0
    )

    connector = _dominant([payment.connector for payment in failures])
    method = _dominant([payment.method for payment in failures])
    region = _dominant([payment.region for payment in failures])

    revenue_at_risk = sum(
        Decimal(str(payment.amount))
        for payment in failures
    )

    signals: list[str] = []

    if failure_rate >= 0.20:
        signals.append("HIGH_FAILURE_RATE")

    if average_latency >= 2000:
        signals.append("HIGH_LATENCY")

    failure_codes = Counter(
        str(payment.failure_code).upper()
        for payment in failures
        if payment.failure_code
    )

    if failure_codes:
        dominant_code, dominant_count = failure_codes.most_common(1)[0]

        if dominant_count / max(len(failures), 1) >= 0.30:
            signals.append(dominant_code)

    connector_count = Counter(
        payment.connector
        for payment in failures
        if payment.connector
    )

    if connector_count and connector_count.most_common(1)[0][1] / max(
        len(failures), 1
    ) >= 0.50:
        signals.append("CONNECTOR_CONCENTRATION")

    incident_score = 0.0

    if failure_rate >= 0.20:
        incident_score += 0.40
    elif failure_rate >= 0.10:
        incident_score += 0.25

    if average_latency >= 3000:
        incident_score += 0.30
    elif average_latency >= 2000:
        incident_score += 0.20

    if connector:
        incident_score += 0.10

    if len(failures) >= 5:
        incident_score += 0.10

    incident_score = min(1.0, round(incident_score, 2))

    incident = incident_score >= 0.40

    if "NETWORK_ERROR" in signals or "TIMEOUT" in signals:
        root_cause = "connector_or_network_degradation"
        recommended_action = "evaluate_connector_reroute"
    elif "CONNECTOR_CONCENTRATION" in signals:
        root_cause = "connector_degradation"
        recommended_action = "evaluate_connector_reroute"
    elif "HIGH_LATENCY" in signals:
        root_cause = "payment_latency_degradation"
        recommended_action = "investigate_latency"
    elif "HIGH_FAILURE_RATE" in signals:
        root_cause = "payment_failure_spike"
        recommended_action = "investigate_failure_spike"
    else:
        root_cause = "no_systemic_incident"
        recommended_action = "continue_observation"

    confidence = round(
        min(
            0.99,
            0.55
            + (0.20 if failure_rate >= 0.20 else 0.0)
            + (0.15 if average_latency >= 2000 else 0.0)
            + (0.09 if connector else 0.0),
        ),
        2,
    )

    severity = severity_from_score(incident_score)

    incident_id = (
        f"INC-{uuid4().hex[:8].upper()}"
        if incident
        else None
    )

    alternative_connector = None
    if connector:
        alternative_connector = (
            "connector_b" if connector == "connector_a" else "connector_a"
        )

    revenue_decision = decide_revenue_intervention(
        revenue_at_risk_per_hour=float(revenue_at_risk),
        affected_payments=len(failures),
        failure_rate=failure_rate,
        confidence=confidence,
        affected_connector=connector,
        alternative_connector=alternative_connector,
        alternative_connector_health=0.90 if incident else 0.0,
        current_connector_health=max(0.0, 1.0 - failure_rate),
    )

    result = {
        "incident_id": incident_id,
        "incident": incident,
        "severity": severity,
        "confidence": confidence,
        "root_cause": root_cause,
        "revenue_at_risk_per_hour": float(revenue_at_risk),
        "affected_payments": len(failures),
        "failure_rate": failure_rate,
        "average_latency_ms": average_latency,
        "affected_connector": connector,
        "affected_method": method,
        "affected_region": region,
        "signals": sorted(set(signals)),
        "recommended_action": recommended_action,
        "window_minutes": window_minutes,
        "revenue_decision": {
            "decision": revenue_decision.decision,
            "action": revenue_decision.action,
            "target_connector": revenue_decision.target_connector,
            "traffic_shift_percent": revenue_decision.traffic_shift_percent,
            "revenue_at_risk_per_hour": revenue_decision.revenue_at_risk_per_hour,
            "expected_revenue_protected_per_hour": revenue_decision.expected_revenue_protected_per_hour,
            "intervention_risk": revenue_decision.intervention_risk,
            "blast_radius": revenue_decision.blast_radius,
            "confidence": revenue_decision.confidence,
            "rollback_required": revenue_decision.rollback_required,
            "reason": revenue_decision.reason,
            "reason_codes": list(revenue_decision.reason_codes),
        },
    }

    logger.warning(
        "incident.commander incident_id=%s severity=%s "
        "root_cause=%s confidence=%s revenue_at_risk_per_hour=%s "
        "affected_payments=%s",
        incident_id,
        severity,
        root_cause,
        confidence,
        revenue_at_risk,
        len(failures),
    )

    return result
