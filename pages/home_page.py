"""
Page Object for the OpenLibrary home page (https://openlibrary.org/).

Responsibilities:
- Navigate to the home page.
- Fill the search input and submit the search form.

Selectors are sourced from selectors_inventory.md (empirically verified).

IMPORTANT: The search submit is <input type="submit">, NOT <button>.
           Never use button[type='submit'] for this page.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.base_page import BasePage

if TYPE_CHECKING:
    from playwright.async_api import Page


class HomePage(BasePage):
    """Page Object for https://openlibrary.org/."""

    PATH = "/"

    # ── Verified selectors (see selectors_inventory.md) ───────────────────────
    # Search input: input[name='q'] is unique (count=1, verified ✅)
    _SEARCH_INPUT_CSS = "input[name='q']"
    _SEARCH_INPUT_FALLBACK_CSS = "[placeholder*='Search' i]"
    _SEARCH_INPUT_XPATH = "//input[@name='q']"

    # Search submit: <input type="submit">, NOT <button> — verified ✅
    _SEARCH_SUBMIT_CSS = "input[type='submit'].search-bar-submit"
    _SEARCH_SUBMIT_FALLBACK_CSS = "[aria-label='Search submit']"

    def __init__(self, page: "Page", base_url: str) -> None:
        super().__init__(page, base_url)

    # ── Template Method hooks ─────────────────────────────────────────────────

    async def _verify_loaded(self) -> None:
        """Confirm the search input is visible before proceeding."""
        await self._locator.find(
            "home_search_input",
            css=self._SEARCH_INPUT_CSS,
            xpath=self._SEARCH_INPUT_XPATH,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def open(self) -> None:
        """Navigate to the home page via the Template Method."""
        await self.navigate(self.PATH)

    async def search(self, query: str) -> None:
        """Fill the search input and submit the search form.

        After this method returns the browser will be on /search?q=<query>.

        Args:
            query: The search term (e.g. ``"Dune"``, ``"Fantastic Mr Fox"``).
        """
        self._logger.info(f"Searching for: {query!r}")

        search_input = await self._locator.find(
            "home_search_input",
            css=self._SEARCH_INPUT_CSS,
            xpath=self._SEARCH_INPUT_XPATH,
        )
        await search_input.fill(query)

        submit = await self._locator.find(
            "home_search_submit",
            css=self._SEARCH_SUBMIT_CSS,
        )
        await submit.click()

        # Wait until the browser has navigated to /search?q=...
        # Use domcontentloaded — OpenLibrary's search page never fully fires
        # the "load" event within a reasonable timeout (lazy-loaded widgets).
        await self._page.wait_for_url(
            "**/search?**",
            timeout=20_000,
            wait_until="domcontentloaded",
        )
        self._logger.info("Navigation to search results complete")
