from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.context_orchestrator import build_ai_context
from app.ai.rag_grounding import build_grounded_prompt
from app.database.connection import get_db
from app.llm.gateway import LLMGateway
from app.llm.providers.gemini import GeminiProvider
from app.models.payment import Payment
from app.services.incident_service import analyze_payment


class AIChatRequest(BaseModel):
    payment_id: str = Field(min_length=1)
    message: str = Field(min_length=1, max_length=4000)


class AIChatResponse(BaseModel):
    payment_id: str
    response: str
    advisory_only: bool = True
    grounded: bool = True


def get_llm_gateway() -> LLMGateway:
    return LLMGateway(GeminiProvider())


router = APIRouter(
    prefix="/api/v1/ai",
    tags=["ai"],
)


@router.post("/chat", response_model=AIChatResponse)
def ai_chat(
    request: AIChatRequest,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_llm_gateway),
):
    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == request.payment_id)
        .first()
    )

    if payment is None:
        raise HTTPException(
            status_code=404,
            detail="Payment not found.",
        )

    incident = analyze_payment(payment)

    context = build_ai_context(
        payment=payment,
        incident=incident,
    )

    prompt = build_grounded_prompt(
        user_prompt=request.message,
        context=context,
    )

    response = gateway.generate(
        prompt=prompt,
        context=context,
    )

    return AIChatResponse(
        payment_id=payment.payment_id,
        response=response,
        advisory_only=True,
        grounded=True,
    )
