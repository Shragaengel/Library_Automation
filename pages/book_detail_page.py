"""
Page Object for OpenLibrary book detail pages (/works/OLXXXXXXX/...).

IMPORTANT UI NOTES
------------------
1. Reading status uses a SINGLE dropdown button group, NOT three buttons:
   - Main button (.book-progress-btn) → adds to Want to Read by default.
   - Arrow button (.book-progress-btn + button) → expands the dropdown.
   - Dropdown options appear after the arrow is clicked.

2. State detection:
   - 'unactivated' in class → book NOT in any shelf.
   - 'activated' (without 'unactivated') → book IS in a shelf.
   - After clicking, always confirm via wait_for_function() — the site can
     silently drop clicks when network is slow.

3. Mobile + desktop layout: h1.work-title appears twice.
   Always use .nth(1) for the desktop (visible) copy.

Selectors sourced from selectors_inventory.md (empirically verified).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.base_page import BasePage

if TYPE_CHECKING:
    from playwright.async_api import Page


class BookDetailPage(BasePage):
    """Page Object for /works/OLXXXXXXX book detail pages."""

    # ── Verified selectors (see selectors_inventory.md) ───────────────────────

    # Reading status button group
    _MAIN_BTN_CSS = ".book-progress-btn"
    _DROPDOWN_ARROW_CSS = ".book-progress-btn + button"

    # Dropdown options (only visible after arrow click)
    _CURRENTLY_READING_CSS = "button.nostyle-btn:has-text('Currently Reading')"
    _ALREADY_READ_CSS = "button.nostyle-btn:has-text('Already Read')"
    _REMOVE_CSS = "button:has-text('Remove From Shelf')"

    # Title — nth(1) because page renders mobile + desktop copies
    _TITLE_CSS = "h1.work-title"

    def __init__(self, page: "Page", base_url: str) -> None:
        super().__init__(page, base_url)

    # ── Template Method hooks ─────────────────────────────────────────────────

    async def _verify_loaded(self) -> None:
        """Hook: wait until the reading-status button is attached to the DOM."""
        await self._page.locator(self._MAIN_BTN_CSS).wait_for(
            state="attached", timeout=10_000
        )

    # ── Navigation ────────────────────────────────────────────────────────────

    async def open(self, absolute_url: str) -> None:
        """Navigate to a book detail page using its full absolute URL.

        Args:
            absolute_url: e.g. ``"https://openlibrary.org/works/OL45804W/Dune"``.
        """
        self._logger.info(f"Opening book: {absolute_url}")
        await self._page.goto(absolute_url, wait_until="domcontentloaded")
        await self._verify_loaded()

    # ── State helpers ─────────────────────────────────────────────────────────

    async def _is_activated(self) -> bool:
        """Return True if the book is currently in any reading shelf."""
        classes = (
            await self._page.locator(self._MAIN_BTN_CSS).get_attribute("class") or ""
        )
        return "activated" in classes and "unactivated" not in classes

    async def _wait_for_activation(self, timeout_ms: int = 5_000) -> None:
        """Block until the main button shows the 'activated' state.

        Uses wait_for_function so the assertion happens in-browser — more
        reliable than polling from Python when the UI updates asynchronously.
        """
        await self._page.wait_for_function(
            """() => {
                const btn = document.querySelector('.book-progress-btn');
                return btn &&
                       btn.classList.contains('activated') &&
                       !btn.classList.contains('unactivated');
            }""",
            timeout=timeout_ms,
        )

    # ── Reading-status actions ─────────────────────────────────────────────────

    async def mark_as_want_to_read(self) -> None:
        """Add book to Want to Read (the default shelf).

        If already in any shelf, this is a no-op.
        Clicks the MAIN button text area — NOT the ▼ arrow.
        """
        if await self._is_activated():
            self._logger.info("Book already in a shelf — skipping Want to Read click")
            return

        self._logger.info("Clicking Want to Read")
        await self._page.locator(self._MAIN_BTN_CSS).click()
        await self._wait_for_activation()
        self._logger.info("Confirmed: book added to Want to Read")

    async def mark_as_already_read(self) -> None:
        """Mark book as Already Read via the dropdown.

        Flow: ensure activated → open dropdown → click 'Already Read'.
        """
        if not await self._is_activated():
            await self.mark_as_want_to_read()

        self._logger.info("Opening dropdown → Already Read")
        await self._page.locator(self._DROPDOWN_ARROW_CSS).click()

        already_read = self._page.locator(self._ALREADY_READ_CSS)
        await already_read.wait_for(state="visible", timeout=3_000)
        await already_read.click()

        # Brief pause for the reading state to register server-side
        await self._page.wait_for_timeout(1_000)
        self._logger.info("Marked as Already Read")

    async def mark_as_currently_reading(self) -> None:
        """Mark book as Currently Reading via the dropdown."""
        if not await self._is_activated():
            await self.mark_as_want_to_read()

        self._logger.info("Opening dropdown → Currently Reading")
        await self._page.locator(self._DROPDOWN_ARROW_CSS).click()

        currently = self._page.locator(self._CURRENTLY_READING_CSS)
        await currently.wait_for(state="visible", timeout=3_000)
        await currently.click()

        await self._page.wait_for_timeout(1_000)
        self._logger.info("Marked as Currently Reading")

    # ── Data extraction ───────────────────────────────────────────────────────

    async def get_title(self) -> str:
        """Return the book title (desktop copy, nth=1)."""
        return (
            await self._page.locator(self._TITLE_CSS).nth(1).inner_text()
        ).strip()

    async def take_screenshot(self, path: str) -> None:
        """Save a viewport screenshot of the current book page.

        Args:
            path: Filesystem path for the PNG file.
        """
        await self._page.screenshot(path=path, full_page=False)
        self._logger.info(f"Screenshot saved: {path}")
