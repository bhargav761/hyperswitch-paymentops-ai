from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


class ConnectorCircuitBreaker:
    def __init__(
        self,
        *,
        failure_threshold: int = 3,
        recovery_timeout_seconds: float = 30.0,
    ):
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1.")
        if recovery_timeout_seconds <= 0:
            raise ValueError("recovery_timeout_seconds must be positive.")

        self.failure_threshold = failure_threshold
        self.recovery_timeout_seconds = recovery_timeout_seconds
        self._states: dict[str, CircuitState] = {}
        self._lock = Lock()

    def _state(self, connector: str) -> CircuitState:
        return self._states.setdefault(connector, CircuitState())

    def is_open(self, connector: str) -> bool:
        with self._lock:
            state = self._state(connector)

            if state.opened_at is None:
                return False

            if monotonic() - state.opened_at >= self.recovery_timeout_seconds:
                state.opened_at = None
                state.failures = 0
                return False

            return True

    def record_success(self, connector: str) -> None:
        with self._lock:
            self._states[connector] = CircuitState()

    def record_failure(self, connector: str) -> None:
        with self._lock:
            state = self._state(connector)
            state.failures += 1

            if state.failures >= self.failure_threshold:
                state.opened_at = monotonic()

    def filter_connectors(self, connectors: list[dict]) -> list[dict]:
        return [
            connector
            for connector in connectors
            if not self.is_open(connector["name"])
        ]

    def snapshot(self) -> dict[str, dict]:
        with self._lock:
            return {
                name: {
                    "failures": state.failures,
                    "open": (
                        state.opened_at is not None
                        and monotonic() - state.opened_at
                        < self.recovery_timeout_seconds
                    ),
                }
                for name, state in self._states.items()
            }


circuit_breaker = ConnectorCircuitBreaker()
