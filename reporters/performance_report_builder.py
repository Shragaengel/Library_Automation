"""
Builder pattern for constructing performance_report.json incrementally.

Supports fluent chaining:
    report = (
        PerformanceReportBuilder()
        .with_environment("dev")
        .with_browser("chromium", "120.0")
        .add_decorated_measurements(collector.get_all())
        .build()
    )
    builder.write_to("reports/performance_report.json")
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


class PerformanceReportBuilder:
    """Builder for performance_report.json.

    Each method returns ``self`` for fluent chaining.
    Call :meth:`build` to finalise the report dict, or :meth:`write_to` to
    build and write to disk in one step.
    """

    def __init__(self) -> None:
        self._report: dict = {
            "run_id": str(uuid.uuid4()),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "ended_at": None,
            "environment": None,
            "browser": None,
            "thresholds": {
                "search_page_ms": 3000,
                "book_page_ms": 2500,
                "reading_list_ms": 2000,
            },
            "measurements": [],
            "summary": {},
        }

    # ── Fluent setters ────────────────────────────────────────────────────────

    def with_environment(self, env: str) -> "PerformanceReportBuilder":
        """Set the target environment label (dev / staging / prod)."""
        self._report["environment"] = env
        return self

    def with_browser(self, name: str, version: str) -> "PerformanceReportBuilder":
        """Set the browser name and version string."""
        self._report["browser"] = {"name": name, "version": version}
        return self

    # ── Measurement adders ────────────────────────────────────────────────────

    def add_page_measurement(
        self,
        url: str,
        metrics: dict,
        threshold_ms: int,
    ) -> "PerformanceReportBuilder":
        """Add a single page-load measurement from capture_page_metrics().

        Args:
            url:          Page URL that was measured.
            metrics:      Dict from capture_page_metrics() with load_time_ms etc.
            threshold_ms: Warn threshold for this page.
        """
        exceeded = metrics.get("load_time_ms", 0) > threshold_ms
        self._report["measurements"].append({
            "type": "page_load",
            "url": url,
            "threshold_ms": threshold_ms,
            "exceeded": exceeded,
            **metrics,
        })
        return self

    def add_decorated_measurements(
        self, measurements: list[dict]
    ) -> "PerformanceReportBuilder":
        """Bulk-add measurements from PerformanceCollector.get_all()."""
        for m in measurements:
            self._report["measurements"].append({
                "type": "decorated_function",
                **m,
            })
        return self

    # ── Terminal operations ───────────────────────────────────────────────────

    def build(self) -> dict:
        """Finalise the report: set ended_at and compute summary.

        Returns:
            The completed report dict (safe to serialise as JSON).
        """
        self._report["ended_at"] = datetime.now(timezone.utc).isoformat()
        self._report["summary"] = self._compute_summary()
        return self._report

    def write_to(self, path: str) -> str:
        """Build and write the report to *path* as JSON.

        The parent directory is created automatically.

        Returns:
            Absolute path string of the written file.
        """
        report = self.build()
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(output)

    # ── Private ───────────────────────────────────────────────────────────────

    def _compute_summary(self) -> dict:
        measurements = self._report["measurements"]
        if not measurements:
            return {"total": 0, "exceeded": 0, "passed": 0, "avg_duration_ms": 0.0}

        durations = [
            m.get("duration_ms") or m.get("load_time_ms") or 0.0
            for m in measurements
        ]
        exceeded_count = sum(1 for m in measurements if m.get("exceeded"))

        return {
            "total": len(measurements),
            "exceeded": exceeded_count,
            "passed": len(measurements) - exceeded_count,
            "avg_duration_ms": round(sum(durations) / len(durations), 2),
            "max_duration_ms": round(max(durations), 2),
        }
