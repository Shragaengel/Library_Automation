"""
Service layer for measuring page-load performance.

Wraps the browser-native Performance API (via page_metrics.py), accumulates
measurements in PerformanceReportBuilder, and writes performance_report.json.

Threshold violations are always logged as WARNINGs — NEVER raised as errors.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reporters.performance_collector import PerformanceCollector
from reporters.performance_report_builder import PerformanceReportBuilder
from utils.logger import get_logger
from utils.page_metrics import capture_page_metrics

if TYPE_CHECKING:
    from playwright.async_api import Page
    from utils.config_loader import Config


class PerformanceService:
    """Measures load times for critical pages and produces performance_report.json.

    Args:
        page:   Playwright Page instance.
        config: Config singleton (for thresholds and report path).
    """

    def __init__(self, page: "Page", config: "Config") -> None:
        self._page = page
        self._config = config
        self._logger = get_logger(self.__class__.__name__)
        self._builder = (
            PerformanceReportBuilder()
            .with_environment(getattr(config, "env_name", "dev"))
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def measure_page_performance(
        self, url: str, threshold_ms: int
    ) -> dict:
        """Navigate to *url*, capture browser metrics, record in report builder.

        Args:
            url:          Full absolute URL to navigate to.
            threshold_ms: Warn if load_time_ms exceeds this value.

        Returns:
            Metrics dict: first_paint_ms, first_contentful_paint_ms,
            dom_content_loaded_ms, load_time_ms.
        """
        self._logger.info(f"Measuring performance: {url}")
        await self._page.goto(url, wait_until="load")
        metrics = await capture_page_metrics(self._page)

        load_ms = metrics.get("load_time_ms", 0)
        exceeded = load_ms > threshold_ms
        if exceeded:
            self._logger.warning(
                f"[PERF] {url} load_time={load_ms}ms "
                f"> threshold {threshold_ms}ms — warning only, not a failure"
            )
        else:
            self._logger.info(f"[PERF] {url} load_time={load_ms}ms OK")

        self._builder.add_page_measurement(
            url=url,
            metrics=metrics,
            threshold_ms=threshold_ms,
        )
        return metrics

    async def measure_all_critical_pages(
        self,
        search_url: str,
        book_url: str,
        reading_list_url: str,
    ) -> None:
        """Measure the three pages required by the exam.

        Thresholds come from config.yaml:
        search=3000ms, book=2500ms, reading_list=2000ms.
        """
        thresholds = getattr(
            self._config,
            "performance_thresholds",
            {"search_page_ms": 3000, "book_page_ms": 2500, "reading_list_ms": 2000},
        )
        await self.measure_page_performance(
            search_url, thresholds.get("search_page_ms", 3000)
        )
        await self.measure_page_performance(
            book_url, thresholds.get("book_page_ms", 2500)
        )
        await self.measure_page_performance(
            reading_list_url, thresholds.get("reading_list_ms", 2000)
        )

    def write_report(self, path: str | None = None) -> str:
        """Merge decorator measurements, build and write report to disk.

        Args:
            path: Output file path. Defaults to config or
                  ``"reports/performance_report.json"``.

        Returns:
            Absolute path of the written JSON file.
        """
        collector = PerformanceCollector()
        self._builder.add_decorated_measurements(collector.get_all())

        output_path = path or getattr(
            self._config,
            "performance_report_path",
            "reports/performance_report.json",
        )
        written = self._builder.write_to(output_path)
        self._logger.info(f"Performance report written: {written}")
        return written
