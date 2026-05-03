"""
Page Object for the OpenLibrary search results page (/search?q=...).

Responsibilities:
- Extract raw BookSearchResult objects from the current page.
- Report whether a next page exists.
- Navigate to the next page.

Filtering and year parsing live in utils/filters.py — NOT here.
Pagination orchestration lives in services/search_service.py — NOT here.

Selectors sourced from selectors_inventory.md (empirically verified).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.base_page import BasePage
from pages.models import BookSearchResult
from utils.exceptions import LocatorNotFoundError

if TYPE_CHECKING:
    from playwright.async_api import Page


class SearchResultsPage(BasePage):
    """Page Object for /search?q=... result pages.

    Exposes raw, unfiltered results from the current page only.
    The service layer is responsible for pagination and filtering.
    """

    # ── Verified selectors (see selectors_inventory.md) ───────────────────────

    # Result item containers (count == number of results on this page)
    _RESULT_ITEMS_CSS = ".searchResultItem"
    _RESULT_ITEMS_FALLBACK_CSS = "ul.list-books > li"

    # Within each result item (used as scoped locators)
    _ITEM_TITLE_CSS = "h3 a"                    # title + href
    _ITEM_TITLE_FALLBACK_CSS = "[itemprop='name']"
    _ITEM_DETAILS_CSS = ".resultDetails"        # prose with year text

    # Pagination — next page
    _NEXT_PAGE_CSS = "[aria-label='Go to next page']"
    _NEXT_PAGE_FALLBACK_CSS = ".pagination-arrow[href*='page=']"

    def __init__(self, page: "Page", base_url: str) -> None:
        super().__init__(page, base_url)

    # ── Template Method hooks ─────────────────────────────────────────────────

    async def _verify_loaded(self) -> None:
        """Wait for DOM content — results may be empty, which is valid."""
        await self._page.wait_for_load_state("domcontentloaded")

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_results_on_page(self) -> list[BookSearchResult]:
        """Extract raw BookSearchResult objects from the current page.

        Returns an empty list when the search yields no results (does NOT raise).
        Individual row failures are logged and skipped — the call never
        fails due to a single bad row.

        Returns:
            List of :class:`~pages.models.BookSearchResult` (may be empty).
        """
        items = self._page.locator(self._RESULT_ITEMS_CSS)
        count = await items.count()

        if count == 0:
            # Try fallback container selector
            items = self._page.locator(self._RESULT_ITEMS_FALLBACK_CSS)
            count = await items.count()

        if count == 0:
            self._logger.info("No result items on this page (empty state)")
            return []

        results: list[BookSearchResult] = []

        for i in range(count):
            item = items.nth(i)
            try:
                # Title and href
                title_loc = item.locator(self._ITEM_TITLE_CSS).first
                if await title_loc.count() == 0:
                    title_loc = item.locator(self._ITEM_TITLE_FALLBACK_CSS).first

                title = (await title_loc.inner_text()).strip()
                href = (await title_loc.get_attribute("href")) or ""

                # Year prose text
                details_loc = item.locator(self._ITEM_DETAILS_CSS).first
                year_text = ""
                if await details_loc.count() > 0:
                    year_text = (await details_loc.inner_text()).strip()

                results.append(BookSearchResult(
                    title=title,
                    year_text=year_text,
                    relative_url=href,
                    absolute_url=self._base_url.rstrip("/") + href,
                ))

            except Exception as exc:
                self._logger.warning(f"Skipping result #{i}: {exc}")
                continue

        self._logger.info(f"Extracted {len(results)} raw results from current page")
        return results

    async def has_next_page(self) -> bool:
        """Return True if a visible next-page link exists.

        Uses LocatorNotFoundError from SmartLocator to detect absence safely.
        """
        try:
            next_btn = await self._locator.find(
                "search_next_page",
                css=self._NEXT_PAGE_CSS,
            )
            return await next_btn.is_visible()
        except LocatorNotFoundError:
            return False
        except Exception as exc:
            self._logger.debug(f"has_next_page check failed: {exc}")
            return False

    async def go_to_next_page(self) -> None:
        """Click the next-page link and wait for the new results to load."""
        next_btn = await self._locator.find(
            "search_next_page",
            css=self._NEXT_PAGE_CSS,
        )
        await next_btn.click()
        await self._page.wait_for_load_state("domcontentloaded")
        # Brief stabilisation — Lit-based pagination renders asynchronously
        await self._page.wait_for_timeout(300)
        self._logger.info("Navigated to next search results page")
