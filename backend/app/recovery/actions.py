from app.recovery.decision_engine import RecoveryDecision
from app.services.logging_service import get_logger

logger = get_logger(__name__)


def prepare_recovery_action(
    decision: RecoveryDecision,
) -> dict:
    result = {
        "executed": False,
        "action": decision.action,
        "confidence": decision.confidence,
        "requires_approval": decision.requires_approval,
        "message": (
            "Recovery action prepared but not executed. "
            "External payment execution requires "
            "validated payment-engine integration."
        ),
    }

    logger.info(
        "recovery.prepared action=%s confidence=%s approval=%s",
        decision.action,
        decision.confidence,
        decision.requires_approval,
    )

    return result
