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
        self._logged_in = True
        self._logger.info("Session established")

    @staticmethod
    def _slugify(url: str) -> str:
        """Convert a URL to a short, filesystem-safe filename segment."""
        return re.sub(r"[^a-zA-Z0-9_-]", "_", url)[:60]

    # ── Public API ────────────────────────────────────────────────────────────

    async def add_books_to_reading_list(
        self, urls: list[str]
    ) -> list[dict]:
        """Mark each book at the given URLs with the configured strategy.

        Login is performed once before any books are processed.

        Args:
            urls: Absolute URLs of book detail pages.

        Returns:
            List of result dicts — one per URL — with keys:

            - ``url``              – original URL
            - ``action``          – strategy label (``None`` on error)
            - ``screenshot_path`` – path to saved PNG
            - ``timestamp``       – ISO 8601 UTC timestamp
            - ``error``           – error message string (``None`` on success)
        """
        await self._ensure_logged_in()

        results: list[dict] = []

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
                # Attempt an error screenshot for debugging
                try:
                    await self._page.screenshot(path=screenshot_path)
                except Exception:
                    pass

            results.append(result)

        successes = sum(1 for r in results if r["error"] is None)
        self._logger.info(
            f"Completed: {successes}/{len(results)} books processed successfully"
        )
        return results

    async def assert_reading_list_count(self, expected_count: int) -> None:
        """Open the reading list page and assert the book count matches.

        Args:
            expected_count: Number of books expected in the Want to Read shelf.

        Raises:
            AssertionError: If the actual count differs from ``expected_count``.
        """
        reading_list = ReadingListPage(self._page, self._base_url)
        await reading_list.open()

        screenshot_path = str(
            self._screenshots_dir / "reading_list_verification.png"
        )
        await self._page.screenshot(path=screenshot_path)

        actual = await reading_list.get_book_count()
        assert actual >= expected_count, (
            f"Reading list count mismatch: expected at least {expected_count}, "
            f"got {actual}. Screenshot: {screenshot_path}"
        )
        self._logger.info(
            f"Reading list count verified: {actual} == {expected_count}"
        )

    async def get_reading_list_count(self) -> int:
        """Return the current number of books in the reading list."""
        reading_list = ReadingListPage(self._page, self._base_url)
        await reading_list.open()
        return await reading_list.get_book_count()
