from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AIDiagnosis:
    root_cause: str
    confidence: float
    evidence: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class AIRecommendation:
    action: str
    confidence: float
    reason: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class AIRecoveryPrediction:
    probability: float
    confidence: float
    rationale: str


@dataclass(frozen=True)
class AIRoutingRecommendation:
    connector: str | None
    confidence: float
    reason: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class AIAnalysis:
    diagnosis: AIDiagnosis
    recovery_prediction: AIRecoveryPrediction
    recommendation: AIRecommendation
    routing: AIRoutingRecommendation
