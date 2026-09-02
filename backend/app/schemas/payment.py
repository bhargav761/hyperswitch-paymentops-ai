from decimal import Decimal

from pydantic import BaseModel, Field


class PaymentEvent(BaseModel):
    payment_id: str = Field(min_length=1, max_length=100)
    event_id: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=10)
    method: str = Field(min_length=1, max_length=50)
    connector: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    status: str = Field(min_length=1, max_length=30)
    failure_code: str | None = Field(default=None, max_length=100)
    failure_reason: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)


class PaymentResponse(BaseModel):
    payment_id: str
    event_id: str
    amount: Decimal
    currency: str
    method: str
    connector: str | None
    region: str | None
    status: str
    failure_code: str | None
    failure_reason: str | None
    latency_ms: int | None
    revenue_at_risk: Decimal
