from __future__ import annotations

from collections import Counter
from threading import Lock
from typing import Dict


class Metrics:
    """Small provider-independent metrics registry for control-plane observability."""

    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = Lock()

    def increment(self, name: str, value: int = 1) -> None:
        if value < 0:
            raise ValueError("Metric increments must be non-negative.")
        with self._lock:
            self._counts[name] += value

    def snapshot(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


metrics = Metrics()
