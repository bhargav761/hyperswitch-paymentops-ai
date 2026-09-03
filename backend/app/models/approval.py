from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.payment import Base


class RecoveryApproval(Base):
    __tablename__ = "recovery_approvals"

    approval_id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
    )

    payment_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        index=True,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING",
    )

    reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    confidence: Mapped[float] = mapped_column(
        nullable=False,
    )

    requested_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="paymentops-ai",
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
