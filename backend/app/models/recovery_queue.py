from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.payment import Base


class RecoveryQueueItem(Base):
    __tablename__ = "recovery_queue_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    payment_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    idempotency_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="QUEUED",
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
