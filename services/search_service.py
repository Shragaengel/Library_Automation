"""
Service layer for the OpenLibrary book-search flow.

Orchestrates:
1. Opening the home page.
2. Submitting a search query.
3. Paginating over search results pages.
4. Filtering results by publish year.
5. Returning up to ``limit`` matching books.

Neither the Page Objects nor the filter utilities contain this orchestration
logic — it lives exclusively here (Single Responsibility Principle).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.home_page import HomePage
from pages.models import BookSearchResult
from pages.search_results_page import SearchResultsPage
from utils.config_loader import Config
from utils.filters import filter_books_by_year
from utils.logger import get_logger

if TYPE_CHECKING:
    from playwright.async_api import Page

_MAX_PAGES = 10          # hard ceiling on pagination to prevent infinite loops
_DEFAULT_LIMIT = 5       # default number of results to return


class SearchService:
    """
    High-level orchestrator for searching books on OpenLibrary.

    Args:
        page:     Playwright Page instance (injected by caller / fixture).
        config:   Config singleton (optional — defaults to ``Config()``).
    """

    def __init__(self, page: "Page", config: Config | None = None) -> None:
        self._page = page
        self._cfg = config or Config()
        self._logger = get_logger(self.__class__.__name__)

    # ── Public API ────────────────────────────────────────────────────────────

    async def search_books_by_title_under_year(
        self,
        query: str,
        max_year: int,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[str]:
        """
        Search for books matching *query* and return up to *limit* URLs
        whose publish year is ≤ *max_year*.

        Flow:
        1. Navigate to the OpenLibrary home page.
        2. Submit the search form with *query*.
        3. On each results page, extract raw results and apply the year filter.
        4. Stop once *limit* filtered results are accumulated or there are no
           more pages (up to :data:`_MAX_PAGES` pages as a safety cap).

        Args:
            query:    Search term (e.g. ``"Dune"``).
            max_year: Inclusive upper bound on the publish year (e.g. ``1980``).
            limit:    Maximum number of results to return (default 5).

        Returns:
            List of absolute URL strings (may be empty).
        """
        books = await self._search_books_internal(
            query=query, max_year=max_year, limit=limit,
        )
        self._last_results = books
        return [b.absolute_url for b in books]

    @property
    def last_results(self) -> list[BookSearchResult]:
        """Return the full BookSearchResult objects from the last search.

        Useful for tests that need to inspect titles, years, etc.
        """
        return getattr(self, "_last_results", [])

    async def _search_books_internal(
        self,
        query: str,
        max_year: int,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[BookSearchResult]:
        """Internal: search and return rich BookSearchResult objects."""
        self._logger.info(
            f"Searching for {query!r}, max_year={max_year}, limit={limit}"
        )

        # Step 1 & 2: Navigate and search
        home = HomePage(self._page, self._cfg.base_url)
        await home.open()
        await home.search(query)

        # Step 3 & 4: Paginate and filter
        results_page = SearchResultsPage(self._page, self._cfg.base_url)
        collected: list[BookSearchResult] = []
        pages_visited = 0

        while len(collected) < limit and pages_visited < _MAX_PAGES:
            pages_visited += 1
            self._logger.debug(f"Processing page {pages_visited}")

            raw = await results_page.get_results_on_page()
            if not raw:
                self._logger.info("Empty page — stopping pagination")
                break

            filtered = filter_books_by_year(raw, max_year)
            self._logger.debug(
                f"Page {pages_visited}: {len(raw)} raw, {len(filtered)} after filter"
            )

            for book in filtered:
                if len(collected) >= limit:
                    break
                collected.append(book)

            if len(collected) >= limit:
                break

            has_next = await results_page.has_next_page()
            if not has_next:
                self._logger.info("No next page — stopping pagination")
                break

            await results_page.go_to_next_page()

        self._logger.info(
            f"Done. Returning {len(collected)} results "
            f"(visited {pages_visited} page(s))"
        )
        return collected
