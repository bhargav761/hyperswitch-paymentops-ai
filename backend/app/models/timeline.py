from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.payment import Base


class RecoveryTimelineEvent(Base):
    __tablename__ = "recovery_timeline_events"

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

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    recovery_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        index=True,
    )

    correlation_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False,
        index=True,
    )
