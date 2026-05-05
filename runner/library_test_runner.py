"""
Facade pattern: single high-level entry point for the complete automation flow.

Hides the complexity of search, reading-list management, performance measurement,
and report generation behind one method: ``run_full_flow()``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from reporters.performance_collector import PerformanceCollector
from services.performance_service import PerformanceService
from services.reading_list_service import ReadingListService
from services.search_service import SearchService
from strategies.reading_strategy import RandomReadingStrategy, ReadingStrategy
from utils.logger import get_logger
from utils.models import Credentials

if TYPE_CHECKING:
    from playwright.async_api import Page
    from utils.config_loader import Config


class LibraryTestRunner:
    """FACADE: composes all services into a single run_full_flow() call.

    Args:
        page:     Playwright Page instance.
        config:   Config singleton.
        strategy: Reading strategy to apply (defaults to RandomReadingStrategy).
    """

    def __init__(
        self,
        page: "Page",
        config: "Config",
        strategy: ReadingStrategy | None = None,
    ) -> None:
        self._page = page
        self._config = config
        self._logger = get_logger(self.__class__.__name__)

        creds = Credentials(
            username=config.username,
            password=config.password,
        )
        self._strategy = strategy or RandomReadingStrategy()
        self._search = SearchService(page, config)
        self._reading = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=self._strategy,
        )
        self._perf = PerformanceService(page, config)

    async def run_full_flow(
        self,
        query: str,
        max_year: int,
        limit: int = 5,
        measure_performance: bool = True,
    ) -> dict:
        """Execute the complete exam flow end-to-end.

        Steps:
          1. Search for books matching *query* up to *max_year* (Task 1).
          2. Optionally measure search-page performance.
          3. Add found books to the reading list (Task 2).
          4. Optionally measure book-page performance.
          5. Verify reading list count (Task 3).
          6. Optionally measure reading-list performance.
          7. Write performance_report.json (Task 4).

        Args:
            query:               Search term.
            max_year:            Inclusive publish-year upper bound.
            limit:               Max books to process.
            measure_performance: Set False to skip page-load timing.

        Returns:
            Summary dict with keys: query, max_year, urls_found, urls_added,
            urls_failed, reading_list_count, verification_passed,
            performance_report_path.
        """
        PerformanceCollector().reset()
        self._logger.info(
            f"run_full_flow: query={query!r}, max_year={max_year}, limit={limit}"
        )

        # ── Task 1: Search ─────────────────────────────────────────────────
        urls = await self._search.search_books_by_title_under_year(
            query=query, max_year=max_year, limit=limit,
        )
        self._logger.info(f"Found {len(urls)} books")

        if measure_performance:
            search_url = f"{self._config.base_url}/search?q={query}"
            await self._perf.measure_page_performance(search_url, threshold_ms=3000)

        # ── Task 2: Add to reading list ────────────────────────────────────
        await self._reading.add_books_to_reading_list(urls)
        results = self._reading.last_add_results
        added = [r for r in results if r["error"] is None]

        if measure_performance and urls:
            await self._perf.measure_page_performance(urls[0], threshold_ms=2500)

        # ── Task 3: Verify count ───────────────────────────────────────────
        # Only count books that were added to "Want to Read" — when using
        # RandomReadingStrategy some books go to "Already Read" and would
        # not appear on the Want-to-Read shelf.
        want_to_read_added = [
            r for r in added if r["action"] == "want-to-read"
        ]
        try:
            await self._reading.assert_reading_list_count(
                len(want_to_read_added)
            )
            verification_passed = True
        except AssertionError:
            verification_passed = False
        # Re-use the count already fetched inside assert_reading_list_count
        # to avoid a second navigation + rate-limit wait.
        actual_count = self._reading.last_verified_count

        reading_list_url = (
            f"{self._config.base_url}/people/{self._config.ol_username}/books/want-to-read"
        )
        if measure_performance:
            await self._perf.measure_page_performance(
                reading_list_url, threshold_ms=2000
            )

        # ── Task 4: Write performance report ──────────────────────────────
        perf_path = self._perf.write_report()

        summary = {
            "query": query,
            "max_year": max_year,
            "urls_found": len(urls),
            "urls_added": len(added),
            "urls_failed": len(results) - len(added),
            "reading_list_count": actual_count,
            "verification_passed": verification_passed,
            "performance_report_path": perf_path,
        }
        self._logger.info(f"Flow complete: {summary}")
        return summary
