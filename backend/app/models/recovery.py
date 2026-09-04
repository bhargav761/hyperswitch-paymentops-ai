from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.models.payment import Base


class RecoveryExecution(Base):
    __tablename__ = "recovery_executions"

    id = Column(Integer, primary_key=True, index=True)
    payment_id = Column(String(100), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    action = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, index=True)
    connector = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
