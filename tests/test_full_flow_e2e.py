"""
E2E tests for LibraryTestRunner (Facade) — the complete four-task flow.

Run with:
    pytest tests/test_full_flow_e2e.py -v -m e2e
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from runner.library_test_runner import LibraryTestRunner
from strategies.reading_strategy import WantToReadStrategy

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e, pytest.mark.requires_auth]


def _has_auth() -> bool:
    return bool(os.getenv("OPENLIBRARY_USER") and os.getenv("OPENLIBRARY_PASS"))


class TestFullFlowE2E:

    async def test_full_flow_dune(self, page, config):
        """run_full_flow returns a valid summary and writes a JSON report."""
        if not _has_auth():
            pytest.skip("Credentials not set in .env")

        runner = LibraryTestRunner(
            page=page,
            config=config,
            strategy=WantToReadStrategy(),
        )
        summary = await runner.run_full_flow(
            query="Dune", max_year=1980, limit=2,
        )

        assert "urls_found" in summary
        assert "urls_added" in summary
        assert "performance_report_path" in summary
        assert summary["urls_found"] >= 0
        assert summary["urls_added"] >= 0

        # Performance report must exist and be valid JSON
        report_path = summary["performance_report_path"]
        assert Path(report_path).exists(), f"Report not found: {report_path}"
        data = json.loads(Path(report_path).read_text(encoding="utf-8"))
        for key in ("run_id", "measurements", "summary"):
            assert key in data, f"Missing key in report: {key}"

    async def test_no_results_query_does_not_crash(self, page, config):
        """A query with zero results should return urls_found=0 without crashing."""
        if not _has_auth():
            pytest.skip("Credentials not set in .env")

        runner = LibraryTestRunner(page=page, config=config)
        summary = await runner.run_full_flow(
            query="qzxasdf123nonexistent999",
            max_year=2000,
            limit=5,
            measure_performance=False,
        )
        assert summary["urls_found"] == 0
        assert summary["urls_added"] == 0

    async def test_summary_structure(self, page, config):
        """Summary dict contains all expected keys."""
        if not _has_auth():
            pytest.skip("Credentials not set in .env")

        runner = LibraryTestRunner(
            page=page, config=config, strategy=WantToReadStrategy()
        )
        summary = await runner.run_full_flow(
            query="Dune", max_year=2000, limit=1, measure_performance=False,
        )
        required_keys = {
            "query", "max_year", "urls_found", "urls_added", "urls_failed",
            "reading_list_count", "verification_passed", "performance_report_path",
        }
        assert required_keys == set(summary.keys()), (
            f"Missing keys: {required_keys - set(summary.keys())}"
        )
