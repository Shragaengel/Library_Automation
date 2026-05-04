"""
Page Object for the OpenLibrary Want-to-Read shelf.

URL pattern: /people/<username>/books/want-to-read
The username is the part BEFORE the @ in the login email — NOT /account/.

Count strategies (applied in order):
  A. Parse from section header text: 'Want to Read (N)'
  B. Detect empty-state banner → return 0
  C. Count .mybooks-list work links (several selector variants) as a fallback
  D. Call the OpenLibrary JSON API (/people/<username>/books/want-to-read.json)
     via fetch() inside the page context so session cookies are sent automatically.
     This is the most reliable strategy and does not depend on the page HTML layout.
  E. Last-resort JS DOM scan — parse page text and count /works/ links.

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
    # Fallback selectors tried in order when the primary selector returns 0
    _BOOK_LINKS_FALLBACKS = (
        ".mybooks-list a[href*='/works/']",
        ".mybooks-list a[href*='/work/']",
        "li[class*='book'] a[href*='/works/']",
        ".list-books a[href*='/works/']",
        "a[href*='/works/OL']",
    )
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
        """Hook: wait for the reading list to settle.

        OpenLibrary renders the book list via JavaScript after the initial
        HTML document is loaded.  We wait for the full 'load' event and then
        for the book-list container (or empty-state banner) to appear.

        NOTE: We intentionally do NOT retry on an error page here.  Sending
        repeated reload requests to a rate-limited endpoint extends the rate-
        limit window.  Retry logic lives in ReadingListService.get_reading_list_count()
        which re-navigates after a fresh sleep instead of reloading.
        """
        try:
            await self._page.wait_for_load_state("load", timeout=15_000)
        except Exception:
            pass

        # Wait for the book list OR the empty-state to be present in the DOM
        try:
            await self._page.wait_for_selector(
                f"{self._CONTAINER_CSS}, .books-list, .list-books",
                timeout=10_000,
            )
        except Exception:
            pass  # empty shelf or unexpected layout — count strategies handle it

    # ── Public API ────────────────────────────────────────────────────────────

    async def open(self) -> None:
        """Navigate to the reading list page via the Template Method."""
        await self.navigate(self._path)

    async def get_book_count(self) -> int:
        """Return the number of books in the Want to Read shelf.

        Tries four strategies in order; the first that succeeds is returned.
        Strategy D (JSON API) is the most reliable as it does not depend on
        the page HTML layout.

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

        # Strategy C: count work links — try several selector variants in case
        # OpenLibrary updated their page structure
        for selector in self._BOOK_LINKS_FALLBACKS:
            count = await self._page.locator(selector).count()
            if count > 0:
                self._logger.info(f"Book count from work links ({selector!r}): {count}")
                return count

        # Strategy D: call the OpenLibrary JSON API via fetch() inside the
        # browser context so that session cookies are sent automatically.
        # Try multiple API path variants — OpenLibrary's API format varies.
        try:
            username = self._username
            if username is None:
                from utils.config_loader import Config
                username = Config().ol_username
            api_paths = [
                f"/people/{username}/books/want-to-read.json",
                f"/people/{username}/books/want-to-read.json?limit=1",
                f"/people/{username}.json",
            ]
            self._logger.info(f"Strategy D: trying JSON API variants for user {username!r}")
            api_result: dict = await self._page.evaluate(
                """async (paths) => {
                    for (const apiPath of paths) {
                        try {
                            const resp = await fetch(apiPath);
                            if (!resp.ok) continue;
                            const data = await resp.json();
                            const keys = Object.keys(data).slice(0, 15);
                            // Direct numFound field
                            if (typeof data.numFound === 'number')
                                return {count: data.numFound, source: 'numFound', path: apiPath, keys: keys};
                            // reading_log_entries array
                            if (Array.isArray(data.reading_log_entries))
                                return {count: data.reading_log_entries.length, source: 'reading_log_entries', path: apiPath, keys: keys};
                            // Nested reading log inside page key
                            if (data.reading_log && typeof data.reading_log['want-to-read'] === 'number')
                                return {count: data.reading_log['want-to-read'], source: 'reading_log', path: apiPath, keys: keys};
                            // Check for shelf counts
                            if (data.counts && typeof data.counts === 'object') {
                                const wtr = data.counts['want-to-read'] || data.counts['want_to_read'] || 0;
                                if (wtr > 0) return {count: wtr, source: 'counts', path: apiPath, keys: keys};
                            }
                            return {count: -1, error: 'unknown shape', path: apiPath, keys: keys};
                        } catch (e) {
                            continue;
                        }
                    }
                    return {count: -1, error: 'all API paths failed'};
                }""",
                api_paths,
            )
            self._logger.info(f"Strategy D result: {api_result}")
            count_api = api_result.get("count", -1)
            if count_api >= 0:
                self._logger.info(f"Book count from JSON API: {count_api}")
                return count_api
            else:
                self._logger.warning(f"JSON API returned no count: {api_result}")
        except Exception as exc:
            self._logger.warning(f"JSON API strategy failed: {exc}")

        # Strategy E: last-resort JS DOM scan — parse text content and count links
        try:
            count_js: int = await self._page.evaluate(
                """() => {
                    const full = document.body ? document.body.innerText : '';
                    const m = full.match(/Want to Read\\s*\\((\\d+)\\)/);
                    if (m) return parseInt(m[1], 10);
                    const links = document.querySelectorAll('a[href*="/works/"]');
                    if (links.length > 0) return links.length;
                    return -1;
                }"""
            )
            if count_js >= 0:
                self._logger.info(f"Book count from JS page scan: {count_js}")
                return count_js
        except Exception as exc:
            self._logger.warning(f"JS page scan failed: {exc}")

        # ── DEBUG: dump page info so we can diagnose why all strategies failed ──
        try:
            debug_info = await self._page.evaluate(
                """() => {
                    return {
                        url: location.href,
                        title: document.title,
                        bodyText: (document.body ? document.body.innerText : '').substring(0, 500),
                        bodyHTML: (document.body ? document.body.innerHTML : '').substring(0, 500),
                    };
                }"""
            )
            self._logger.warning(f"DEBUG page state: url={debug_info.get('url')}, title={debug_info.get('title')}")
            self._logger.warning(f"DEBUG body text (first 500 chars): {debug_info.get('bodyText', '')}")
        except Exception:
            pass

        self._logger.warning(
            "All count strategies exhausted — returning 0. "
            "The page may not have loaded yet or the selectors are outdated."
        )
        return 0

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
