from app.models.recovery import RecoveryExecution


def test_recovery_execution_model_metadata():
    assert RecoveryExecution.__tablename__ == "recovery_executions"

    columns = RecoveryExecution.__table__.columns

    assert columns["payment_id"].nullable is False
    assert columns["idempotency_key"].nullable is False
    assert columns["action"].nullable is False
    assert columns["status"].nullable is False
    assert columns["attempt_count"].default.arg == 0
