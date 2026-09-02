from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Payment(Base):
    __tablename__ = "payments"

    payment_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    event_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="INR",
    )
    method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    connector: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )
    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    latency_ms: Mapped[int | None] = mapped_column(
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
