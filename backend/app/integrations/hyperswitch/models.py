from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HyperswitchPaymentResult:
    success: bool
    payment_id: str
    status: str
    raw: dict[str, Any]
    error_code: str | None = None
    error_message: str | None = None
