from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment
from app.services.incident_service import analyze_payment

router = APIRouter(
    prefix="/api/v1/incidents",
    tags=["incidents"],
)


@router.get("/analyze/{payment_id}")
def analyze_incident(
    payment_id: str,
    db: Session = Depends(get_db),
):
    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="Payment not found",
        )

    return analyze_payment(payment)
