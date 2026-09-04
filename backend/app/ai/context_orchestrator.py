from typing import Any

from app.ai.evidence import build_payment_evidence
from app.models.payment import Payment
from app.rag.retriever import retrieve_recovery_guidance


def build_ai_context(
    *,
    payment: Payment,
    incident: dict[str, Any],
    guidance_limit: int = 3,
) -> dict[str, Any]:
    """Assemble bounded PaymentOps evidence and RAG context for an LLM."""

    evidence = build_payment_evidence(
        payment=payment,
        incident=incident,
    )

    guidance = retrieve_recovery_guidance(
        failure_code=payment.failure_code,
        failure_reason=payment.failure_reason,
        status=payment.status,
        limit=guidance_limit,
    )

    return {
        "payment": evidence["payment"],
        "incident": evidence["incident"],
        "recovery_guidance": guidance,
    }
