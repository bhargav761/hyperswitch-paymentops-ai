from dataclasses import dataclass


@dataclass
class AnomalyResult:
    is_anomaly: bool
    score: float
    signals: list[str]


def detect_payment_anomaly(
    status: str,
    failure_code: str | None,
    latency_ms: int | None,
) -> AnomalyResult:
    score = 0.0
    signals: list[str] = []

    if status.lower() == "failed":
        score += 0.55
        signals.append("payment_failed")

    if status.lower() == "pending":
        score += 0.30
        signals.append("payment_pending")

    if failure_code:
        score += 0.15
        signals.append(f"failure_code:{failure_code}")

    if latency_ms is not None:
        if latency_ms >= 5000:
            score += 0.30
            signals.append("very_high_latency")
        elif latency_ms >= 2000:
            score += 0.15
            signals.append("high_latency")

    score = min(score, 1.0)

    return AnomalyResult(
        is_anomaly=score >= 0.50,
        score=round(score, 2),
        signals=signals,
    )
