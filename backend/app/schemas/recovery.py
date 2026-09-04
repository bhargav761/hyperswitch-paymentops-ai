from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class RecoveryExecutionCreate(BaseModel):
    payment_id: str
    idempotency_key: str
    action: str
    status: str
    connector: Optional[str] = None
    confidence: Optional[float] = None


class RecoveryExecutionResponse(BaseModel):
    id: int
    payment_id: str
    idempotency_key: str
    action: str
    status: str
    connector: Optional[str] = None
    confidence: Optional[float] = None
    attempt_count: int
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
