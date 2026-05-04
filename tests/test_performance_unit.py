"""
Unit tests for the performance measurement subsystem.

All tests are fully offline — no Playwright, no browser, no network.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from decorators.measure_performance import measure_performance
from reporters.performance_collector import PerformanceCollector
from reporters.performance_report_builder import PerformanceReportBuilder


# ══════════════════════════════════════════════════════════════════════════════
# PerformanceCollector
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformanceCollector:

    def setup_method(self):
        PerformanceCollector().reset()

    def test_singleton_returns_same_instance(self):
        a = PerformanceCollector()
        b = PerformanceCollector()
        assert a is b

    def test_record_and_retrieve(self):
        col = PerformanceCollector()
        col.record("search", 1500.0, 3000, False)
        col.record("book",   3500.0, 2500, True)
        all_m = col.get_all()
        assert len(all_m) == 2
        assert all_m[0]["page_name"] == "search"
        assert all_m[0]["exceeded"] is False
        assert all_m[1]["page_name"] == "book"
        assert all_m[1]["exceeded"] is True

    def test_get_all_returns_defensive_copy(self):
        col = PerformanceCollector()
        col.record("x", 100.0, 200, False)
        copy = col.get_all()
        copy.append({"bogus": True})
        assert len(col.get_all()) == 1  # original unchanged

    def test_reset_clears_measurements(self):
        col = PerformanceCollector()
        col.record("x", 100.0, 200, False)
        col.reset()
        assert col.get_all() == []

    def test_record_rounds_duration(self):
        PerformanceCollector().record("p", 1234.5678, 2000, False)
        m = PerformanceCollector().get_all()[0]
        assert m["duration_ms"] == round(1234.5678, 2)

    def test_record_includes_timestamp(self):
        PerformanceCollector().record("p", 100.0, 200, False)
        m = PerformanceCollector().get_all()[0]
        assert "timestamp" in m
        assert "T" in m["timestamp"]  # ISO 8601


# ══════════════════════════════════════════════════════════════════════════════
# PerformanceReportBuilder
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformanceReportBuilder:

    def test_build_has_required_keys(self):
        report = PerformanceReportBuilder().build()
        for key in ("run_id", "started_at", "ended_at", "summary", "measurements"):
            assert key in report, f"Missing key: {key}"

    def test_build_sets_ended_at(self):
        report = PerformanceReportBuilder().build()
        assert report["ended_at"] is not None

    def test_write_to_creates_valid_json(self, tmp_path):
        path = str(tmp_path / "perf.json")
        PerformanceReportBuilder().with_environment("test").write_to(path)
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        assert data["environment"] == "test"
        assert "run_id" in data

    def test_summary_exceeded_count(self):
        builder = PerformanceReportBuilder()
        builder._report["measurements"] = [
            {"duration_ms": 100, "exceeded": False},
            {"duration_ms": 200, "exceeded": True},
            {"duration_ms": 300, "exceeded": True},
        ]
        report = builder.build()
        assert report["summary"]["exceeded"] == 2
        assert report["summary"]["passed"] == 1
        assert report["summary"]["total"] == 3

    def test_summary_avg_duration(self):
        builder = PerformanceReportBuilder()
        builder._report["measurements"] = [
            {"duration_ms": 100, "exceeded": False},
            {"duration_ms": 300, "exceeded": False},
        ]
        report = builder.build()
        assert report["summary"]["avg_duration_ms"] == 200.0

    def test_fluent_chaining(self):
        report = (
            PerformanceReportBuilder()
            .with_environment("staging")
            .with_browser("chromium", "120")
            .build()
        )
        assert report["environment"] == "staging"
        assert report["browser"]["name"] == "chromium"
        assert report["browser"]["version"] == "120"

    def test_add_decorated_measurements(self):
        measurements = [
            {"page_name": "home", "duration_ms": 500, "threshold_ms": 1000,
             "exceeded": False, "timestamp": "2024-01-01T00:00:00+00:00"},
        ]
        report = (
            PerformanceReportBuilder()
            .add_decorated_measurements(measurements)
            .build()
        )
        assert len(report["measurements"]) == 1
        assert report["measurements"][0]["type"] == "decorated_function"

    def test_empty_measurements_summary(self):
        report = PerformanceReportBuilder().build()
        assert report["summary"]["total"] == 0
        assert report["summary"]["avg_duration_ms"] == 0.0

    def test_write_creates_parent_directories(self, tmp_path):
        path = str(tmp_path / "nested" / "dir" / "perf.json")
        PerformanceReportBuilder().write_to(path)
        assert Path(path).exists()


# ══════════════════════════════════════════════════════════════════════════════
# @measure_performance decorator
# ══════════════════════════════════════════════════════════════════════════════

class TestMeasurePerformanceDecorator:

    def setup_method(self):
        PerformanceCollector().reset()

    async def test_records_to_collector(self):
        @measure_performance(threshold_ms=5000, page_name="test_page")
        async def fast_func():
            return 42

        result = await fast_func()
        assert result == 42
        measurements = PerformanceCollector().get_all()
        assert len(measurements) == 1
        assert measurements[0]["page_name"] == "test_page"
        assert measurements[0]["exceeded"] is False

    async def test_does_not_raise_on_threshold_exceeded(self):
        """Threshold exceeded MUST NOT raise — only log WARNING."""
        @measure_performance(threshold_ms=1, page_name="slow_page")
        async def slow_func():
            import asyncio
            await asyncio.sleep(0.05)  # 50ms >> 1ms threshold
            return "done"

        result = await slow_func()  # must not raise
        assert result == "done"
        assert PerformanceCollector().get_all()[0]["exceeded"] is True

    async def test_preserves_return_value(self):
        @measure_performance(threshold_ms=1000, page_name="p")
        async def func_with_value():
            return {"key": "value"}

        result = await func_with_value()
        assert result == {"key": "value"}

    async def test_multiple_calls_accumulate(self):
        @measure_performance(threshold_ms=1000, page_name="multi")
        async def task():
            pass

        for _ in range(3):
            await task()

        assert len(PerformanceCollector().get_all()) == 3

    async def test_preserves_function_metadata(self):
        @measure_performance(threshold_ms=1000, page_name="meta_test")
        async def my_named_function():
            """Docstring."""

        assert my_named_function.__name__ == "my_named_function"
        assert my_named_function.__doc__ == "Docstring."
