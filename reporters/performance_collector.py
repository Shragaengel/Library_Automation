"""
Singleton that accumulates performance measurements during a test run.

Measurements are added by the @measure_performance decorator and by
PerformanceService; PerformanceReportBuilder drains them at report-write time.
"""

from __future__ import annotations

from datetime import datetime, timezone


class PerformanceCollector:
    """Singleton accumulator for performance decorator / service output.

    Thread-safe for single-threaded async usage (no concurrent writes).
    """

    _instance: "PerformanceCollector | None" = None
    _measurements: list[dict]

    def __new__(cls) -> "PerformanceCollector":
        if cls._instance is None:
            inst = super().__new__(cls)
            inst._measurements = []
            cls._instance = inst
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────────────

    def record(
        self,
        page_name: str,
        duration_ms: float,
        threshold_ms: int,
        exceeded: bool,
    ) -> None:
        """Append one measurement."""
        self._measurements.append({
            "page_name": page_name,
            "duration_ms": round(duration_ms, 2),
            "threshold_ms": threshold_ms,
            "exceeded": exceeded,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    def get_all(self) -> list[dict]:
        """Return a defensive copy of all recorded measurements."""
        return list(self._measurements)

    def reset(self) -> None:
        """Clear all measurements. Call at the start of each test that checks metrics."""
        self._measurements.clear()
