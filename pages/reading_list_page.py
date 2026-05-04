"""
Page Object for the OpenLibrary Want-to-Read shelf.

URL pattern: /people/<username>/books/want-to-read
The username is the part BEFORE the @ in the login email — NOT /account/.

Count strategies (applied in order):
  A. Parse from section header text: 'Want to Read (N)'
  B. Detect empty-state banner → return 0
  C. Count .mybooks-list work links as a fallback

Selectors sourced from selectors_inventory.md (empirically verified).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from pages.base_page import BasePage

if TYPE_CHECKING:
    from playwright.async_api import Page


class ReadingListPage(BasePage):
    """Page Object for /people/<username>/books/want-to-read."""

    # ── Verified selectors (see selectors_inventory.md) ───────────────────────
    _CONTAINER_CSS = ".mybooks-list"
    _EMPTY_TEXT = "You haven't added any books to this shelf yet."
    _BOOK_LINKS_CSS = ".mybooks-list a[href*='/works/']"
    # The count header matches e.g. "Want to Read (12)"
    _COUNT_HEADER_RE = re.compile(r"Want to Read\s*\((\d+)\)")

    def __init__(
        self,
        page: "Page",
        base_url: str,
        username: str | None = None,
    ) -> None:
        super().__init__(page, base_url)

        self._username = username  # None → resolved lazily in _path

    # ── Template Method hooks ─────────────────────────────────────────────────

    @property
    def _path(self) -> str:
        username = self._username
        if username is None:
            from utils.config_loader import Config
            username = Config().ol_username
        return f"/people/{username}/books/want-to-read"

    async def _verify_loaded(self) -> None:
        """Hook: wait for DOM content — empty shelf is a valid state."""
        await self._page.wait_for_load_state("domcontentloaded")

    # ── Public API ────────────────────────────────────────────────────────────

    async def open(self) -> None:
        """Navigate to the reading list page via the Template Method."""
        await self.navigate(self._path)

    async def get_book_count(self) -> int:
        """Return the number of books in the Want to Read shelf.

        Tries three strategies in order; the first that succeeds is returned.

        Returns:
            Integer count (0 when the shelf is empty).
        """
        # Strategy A: parse from the section-header text
        try:
            header_locs = self._page.locator("text=/Want to Read/")
            count_locs = await header_locs.count()
            for i in range(count_locs):
                text = await header_locs.nth(i).inner_text()
                match = self._COUNT_HEADER_RE.search(text)
                if match:
                    n = int(match.group(1))
                    self._logger.info(f"Book count from header: {n}")
                    return n
        except Exception:
            pass

        # Strategy B: empty-state banner
        empty_loc = self._page.get_by_text(self._EMPTY_TEXT, exact=True)
        if await empty_loc.count() > 0:
            self._logger.info("Empty-state banner detected — count is 0")
            return 0

        # Strategy C: count work links
        count = await self._page.locator(self._BOOK_LINKS_CSS).count()
        self._logger.info(f"Book count from work links: {count}")
        return count

    async def get_book_titles(self) -> list[str]:
        """Return all visible book titles on the reading list page."""
        links = self._page.locator(self._BOOK_LINKS_CSS)
        total = await links.count()
        titles: list[str] = []
        for i in range(total):
            try:
                text = (await links.nth(i).inner_text()).strip()
                if text:
                    titles.append(text)
            except Exception:
                pass
        return titles
