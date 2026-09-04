from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.payment import Payment
from app.services.incident_commander import analyze_system_incident
from app.services.remediation_planner import build_remediation_plan
from app.services.gitops_controller import build_argo_rollout, build_gitops_change
from app.services.revenue_observability import (
    build_revenue_reliability_snapshot,
    snapshot_to_dict,
)
from app.services.closed_loop_verification import verify_recovery

router = APIRouter(
    prefix="/api/v1/revenue-reliability",
    tags=["revenue-reliability"],
)


@router.get("/analyze")
def analyze_revenue_reliability(
    window_minutes: int = Query(default=60, ge=1, le=1440),
    db: Session = Depends(get_db),
):
    payments = db.query(Payment).order_by(Payment.created_at.desc()).all()

    incident = analyze_system_incident(
        payments,
        window_minutes=window_minutes,
    )

    return {
        "incident": incident,
        "revenue_decision": incident.get("revenue_decision"),
    }


@router.post("/plan/{payment_id}")
def create_reliability_plan(
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

    payments = (
        db.query(Payment)
        .filter(
            Payment.connector == payment.connector,
            Payment.region == payment.region,
        )
        .order_by(Payment.created_at.desc())
        .all()
    )

    incident = analyze_system_incident(payments)

    decision_data = incident.get("revenue_decision", {})

    decision = type(
        "RevenueDecisionInput",
        (),
        {
            "decision": decision_data.get("decision", "OBSERVE"),
            "action": decision_data.get(
                "action",
                "CONTINUE_OBSERVATION",
            ),
            "target_connector": decision_data.get("target_connector"),
            "traffic_shift_percent": decision_data.get(
                "traffic_shift_percent",
                0,
            ),
            "expected_revenue_protected_per_hour": decision_data.get(
                "expected_revenue_protected_per_hour",
                0.0,
            ),
        },
    )()

    plan = build_remediation_plan(
        decision=decision,
        observation_window_seconds=300,
    )

    return {
        "payment_id": payment_id,
        "incident": incident,
        "plan": {
            "plan_id": plan.plan_id,
            "status": plan.status,
            "action": plan.action,
            "target_connector": plan.target_connector,
            "traffic_shift_percent": plan.traffic_shift_percent,
            "observation_window_seconds": plan.observation_window_seconds,
            "steps": list(plan.steps),
            "success_criteria": list(plan.success_criteria),
            "rollback_triggers": list(plan.rollback_triggers),
            "rollback_action": plan.rollback_action,
            "expected_revenue_protected_per_hour": (
                plan.expected_revenue_protected_per_hour
            ),
        },
    }


@router.post("/gitops/{payment_id}")
def create_gitops_rollout(
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

    payments = (
        db.query(Payment)
        .filter(
            Payment.connector == payment.connector,
            Payment.region == payment.region,
        )
        .order_by(Payment.created_at.desc())
        .all()
    )

    incident = analyze_system_incident(payments)
    decision_data = incident["revenue_decision"]

    decision = type(
        "RevenueDecisionInput",
        (),
        {
            "decision": decision_data["decision"],
            "action": decision_data["action"],
            "target_connector": decision_data["target_connector"],
            "traffic_shift_percent": decision_data["traffic_shift_percent"],
            "expected_revenue_protected_per_hour": (
                decision_data["expected_revenue_protected_per_hour"]
            ),
        },
    )()

    plan = build_remediation_plan(decision=decision)

    change = build_gitops_change(
        plan=plan,
        confidence=decision_data["confidence"],
        intervention_risk=decision_data["intervention_risk"],
    )

    rollout = build_argo_rollout(
        change=change,
        observation_window_seconds=plan.observation_window_seconds,
    )

    return {
        "incident_id": incident["incident_id"],
        "plan_id": plan.plan_id,
        "change": {
            "change_id": change.change_id,
            "repository": change.repository,
            "manifest_path": change.manifest_path,
            "target_connector": change.target_connector,
            "traffic_shift_percent": change.traffic_shift_percent,
            "commit_message": change.commit_message,
            "validation_status": change.validation_status,
            "rollout_strategy": change.rollout_strategy,
            "rollback_strategy": change.rollback_strategy,
        },
        "rollout": rollout,
    }


@router.post("/verify/{payment_id}")
def verify_revenue_reliability(
    payment_id: str,
    failure_rate_before: float = Query(..., ge=0, le=1),
    failure_rate_after: float = Query(..., ge=0, le=1),
    latency_before_ms: float = Query(..., ge=0),
    latency_after_ms: float = Query(..., ge=0),
    revenue_at_risk_before_per_hour: float = Query(..., ge=0),
    revenue_at_risk_after_per_hour: float = Query(..., ge=0),
    payments_recovered: int = Query(default=0, ge=0),
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

    incident = analyze_system_incident([payment])

    verification = verify_recovery(
        failure_rate_before=failure_rate_before,
        failure_rate_after=failure_rate_after,
        latency_before_ms=latency_before_ms,
        latency_after_ms=latency_after_ms,
        revenue_at_risk_before_per_hour=(
            revenue_at_risk_before_per_hour
        ),
        revenue_at_risk_after_per_hour=(
            revenue_at_risk_after_per_hour
        ),
        payments_recovered=payments_recovered,
    )

    snapshot = build_revenue_reliability_snapshot(
        correlation_id=f"payment-{payment_id}",
        incident=incident,
        verification=verification,
        timeline=(
            "INCIDENT_DETECTED",
            "VERIFICATION",
            verification.status,
        ),
    )

    return snapshot_to_dict(snapshot)
