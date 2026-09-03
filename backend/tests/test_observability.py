from app.observability import Metrics


def test_metrics_increment_snapshot_and_reset():
    metrics = Metrics()
    metrics.increment("ai_analyses")
    metrics.increment("ai_analyses", 2)
    metrics.increment("policy_decisions")

    assert metrics.snapshot() == {
        "ai_analyses": 3,
        "policy_decisions": 1,
    }

    metrics.reset()
    assert metrics.snapshot() == {}


def test_metrics_recovery_outcome_counters():
    metrics = Metrics()

    metrics.increment("recovery_executions")
    metrics.increment("recovery_successes")
    metrics.increment("recovery_executions")
    metrics.increment("recovery_failures")
    metrics.increment("approval_required")

    assert metrics.snapshot() == {
        "recovery_executions": 2,
        "recovery_successes": 1,
        "recovery_failures": 1,
        "approval_required": 1,
    }
