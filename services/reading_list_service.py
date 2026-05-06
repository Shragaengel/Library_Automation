"""
Service layer for adding books to the OpenLibrary reading list.

Orchestrates:
1. Login once per service lifetime (cached via self._logged_in flag).
2. Navigate to each book URL, apply the reading strategy, save a screenshot.
3. Assert or retrieve the reading-list count.

Design decisions
----------------
- Login is performed ONCE and reused for all subsequent book URLs.
- Individual book failures are caught and recorded — one failure does NOT
  stop processing of remaining books.
- Screenshots are saved per book for Allure / debugging evidence.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

import asyncio

from pages.book_detail_page import BookDetailPage
from pages.login_page import LoginPage
from pages.reading_list_page import ReadingListPage
from strategies.reading_strategy import ReadingStrategy
from utils.logger import get_logger
from utils.models import Credentials

if TYPE_CHECKING:
    from playwright.async_api import Page


class ReadingListService:
    """High-level orchestrator for login and reading-list management.

    Args:
        page:             Playwright Page instance (injected by fixture).
        base_url:         Site base URL, e.g. ``"https://openlibrary.org"``.
        credentials:      Login credentials (from Config or .env).
        strategy:         Reading strategy applied to every book.
        screenshots_dir:  Directory for per-book screenshots (created if missing).
    """

    def __init__(
        self,
        page: "Page",
        base_url: str,
        credentials: Credentials,
        strategy: ReadingStrategy,
        screenshots_dir: str = "screenshots",
    ) -> None:
        self._page = page
        self._base_url = base_url
        self._creds = credentials
        self._strategy = strategy
        self._screenshots_dir = Path(screenshots_dir)
        self._screenshots_dir.mkdir(parents=True, exist_ok=True)
        self._logger = get_logger(self.__class__.__name__)
        self._logged_in = False

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _ensure_logged_in(self) -> None:
        """Login once and cache the session state. Subsequent calls are no-ops."""
        if self._logged_in:
            return

        login_page = LoginPage(self._page, self._base_url)
        await login_page.open()
        await login_page.login(self._creds.username, self._creds.password)
        assert await login_page.is_logged_in(), (
            "Login failed silently — credentials may be incorrect"
        )
        self._logged_in = True
        self._logger.info("Session established")

    @staticmethod
    def _slugify(url: str) -> str:
        """Convert a URL to a short, filesystem-safe filename segment."""
        return re.sub(r"[^a-zA-Z0-9_-]", "_", url)[:60]

    # ── Public API ────────────────────────────────────────────────────────────

    async def add_books_to_reading_list(
        self, urls: list[str]
    ) -> None:
        """Mark each book at the given URLs with the configured strategy.

        Login is performed once before any books are processed.
        Results are stored in :attr:`last_add_results` for inspection.

        Args:
            urls: Absolute URLs of book detail pages.
        """
        await self._ensure_logged_in()

        self._last_add_results: list[dict] = []

        for url in urls:
            timestamp = datetime.now(timezone.utc).isoformat()
            screenshot_path = str(
                self._screenshots_dir / f"{self._slugify(url)}.png"
            )
            result: dict = {
                "url": url,
                "action": None,
                "screenshot_path": screenshot_path,
                "timestamp": timestamp,
                "error": None,
            }

            try:
                book_page = BookDetailPage(self._page, self._base_url)
                await book_page.open(url)

                title = await book_page.get_title()
                self._logger.info(f"Processing: {title!r}")

                action = await self._strategy.mark(book_page)
                result["action"] = action

                await book_page.take_screenshot(screenshot_path)
                self._logger.info(
                    f"Done: {title!r} -> {action!r}, screenshot: {screenshot_path}"
                )

            except Exception as exc:
                result["error"] = str(exc)
                self._logger.error(f"Failed for {url!r}: {exc}")
                try:
                    await self._page.screenshot(path=screenshot_path)
                except Exception:
                    pass

            self._last_add_results.append(result)

        successes = sum(1 for r in self._last_add_results if r["error"] is None)
        self._logger.info(
            f"Completed: {successes}/{len(self._last_add_results)} books processed successfully"
        )

    @property
    def last_add_results(self) -> list[dict]:
        """Results from the last add_books_to_reading_list call.

        Each dict has keys: url, action, screenshot_path, timestamp, error.
        """
        return getattr(self, "_last_add_results", [])

    async def assert_reading_list_count(self, expected_count: int) -> None:
        """Open the reading list page and assert the book count matches.

        The actual count is stored in :attr:`last_verified_count` so callers
        can read it without triggering a second navigation.

        Args:
            expected_count: Number of books expected in the Want to Read shelf.

        Raises:
            AssertionError: If the actual count differs from ``expected_count``.
        """
        actual_count = await self.get_reading_list_count()
        self._last_verified_count = actual_count

        screenshot_path = str(
            self._screenshots_dir / "reading_list_verification.png"
        )
        await self._page.screenshot(path=screenshot_path)

        assert actual_count == expected_count, (
            f"Reading list count mismatch: expected {expected_count}, "
            f"got {actual_count}. Screenshot: {screenshot_path}"
        )
        self._logger.info(
            f"Reading list count verified: {actual_count} == {expected_count}"
        )

    @property
    def last_verified_count(self) -> int:
        """The actual book count from the last assert_reading_list_count call."""
        return getattr(self, "_last_verified_count", 0)

    async def _is_error_page(self) -> bool:
        """Detect whether the current page is an OpenLibrary error page."""
        try:
            title = await self._page.title()
            if "Internal Error" in title or "Problem" in title:
                return True
            has_error = await self._page.locator(
                "text=/A Problem Occurred|We're sorry, a problem occurred/"
            ).count()
            return has_error > 0
        except Exception:
            return False

    async def _try_api_count_from_homepage(self) -> int:
        """Try fetching the reading list count via JSON API from a non-error page.

        When the reading-list HTML page returns a 500 error, fetch()
        calls made from that page context also tend to fail.  This helper
        navigates to the homepage first (which is unlikely to be rate-limited)
        and runs the API call from there.
        """
        try:
            from utils.config_loader import Config
            username = Config().ol_username
            api_path = f"/people/{username}/books/want-to-read.json"

            self._logger.info(
                f"Trying JSON API from homepage context: {api_path}"
            )
            await self._page.goto(f"{self._base_url}/", wait_until="load", timeout=15_000)
            result: dict = await self._page.evaluate(
                """async (apiPath) => {
                    try {
                        const resp = await fetch(apiPath);
                        if (!resp.ok)
                            return {count: -1, error: 'HTTP ' + resp.status};
                        const data = await resp.json();
                        if (typeof data.numFound === 'number')
                            return {count: data.numFound, source: 'numFound'};
                        if (Array.isArray(data.reading_log_entries))
                            return {count: data.reading_log_entries.length, source: 'entries'};
                        return {count: -1, error: 'unexpected shape', keys: Object.keys(data).slice(0, 10)};
                    } catch (e) {
                        return {count: -1, error: String(e)};
                    }
                }""",
                api_path,
            )
            self._logger.info(f"Homepage API result: {result}")
            return result.get("count", -1)
        except Exception as exc:
            self._logger.warning(f"Homepage API attempt failed: {exc}")
            return -1

    async def get_reading_list_count(self) -> int:
        """Return the current number of books in the reading list.

        OpenLibrary rate-limits the reading-list endpoint for ~20-30 s after
        book additions.  Under heavy rate-limiting, the page may return a
        500 Internal Error.  Sending reload requests during that window
        extends the rate-limit further.

        Strategy:
          1. Sleep upfront (no requests) to let the rate-limit window pass.
          2. Navigate to the reading list and try to read the count.
          3. If the page is an error page or count is 0, wait longer and retry
             with increasing backoff (up to 3 attempts total).
          4. As a fallback, try the JSON API from the homepage context.
        """
        from utils.config_loader import Config
        wait_times = Config().get("reading_list_wait_times", [30, 40, 50])

        reading_list = ReadingListPage(self._page, self._base_url)

        for attempt, wait_s in enumerate(wait_times, start=1):
            self._logger.info(
                f"Attempt {attempt}/{len(wait_times)}: waiting {wait_s}s "
                f"before reading list (rate-limit buffer)..."
            )
            await asyncio.sleep(wait_s)

            await reading_list.open()

            # Check if we got an error page
            if await self._is_error_page():
                self._logger.warning(
                    f"Attempt {attempt}: OpenLibrary returned an error page "
                    f"— will retry after longer wait"
                )
                continue

            count = await reading_list.get_book_count()
            if count > 0:
                return count

            self._logger.warning(
                f"Attempt {attempt}: reading list count is 0"
            )

        # All page-based attempts failed — try JSON API from homepage context
        self._logger.info("All page attempts failed — trying JSON API from homepage")
        api_count = await self._try_api_count_from_homepage()
        if api_count > 0:
            return api_count

        self._logger.warning(
            "All reading list count strategies failed after all retries"
        )
        return 0
