from decimal import Decimal

from pydantic import BaseModel, Field


class HyperswitchWebhookEvent(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    payment_id: str = Field(min_length=1, max_length=100)
    status: str = Field(min_length=1, max_length=30)
    amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    method: str | None = Field(default=None, max_length=50)
    connector: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    failure_code: str | None = Field(default=None, max_length=100)
    failure_reason: str | None = None
    latency_ms: int | None = Field(default=None, ge=0)
