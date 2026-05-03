"""
BasePage — abstract parent for every Page Object in this suite.

Design patterns applied here:
- Page Object  : encapsulates all interaction with a single web page.
- Template Method: navigate() defines the invariant skeleton; subclasses
                   override lightweight hook methods to customise behaviour.
"""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import ConsoleMessage, Page

from utils.config_loader import Config
from utils.logger import get_logger
from utils.smart_locator import SmartLocator, build_default_chain


class BasePage(ABC):
    """
    Abstract parent for all Page Object classes.

    Subclasses should:
    - Override ``_after_navigate`` to dismiss cookie banners, wait for a
      hero element, etc.
    - Override ``_verify_loaded`` to assert the correct URL / heading is
      present before proceeding.
    - Override ``_before_navigate`` when pre-flight actions are needed
      (e.g., clearing local storage).
    """

    def __init__(self, page: "Page", base_url: str) -> None:
        self._page = page
        self._base_url = base_url.rstrip("/")
        self._logger = get_logger(self.__class__.__name__)
        self._locator = SmartLocator(page, build_default_chain())
        self._console_errors: list[str] = []

        # Passively capture browser console errors for later inspection.
        self._page.on("console", self._on_console_message)

    # ── Private event listener ─────────────────────────────────────────────────

    def _on_console_message(self, msg: "ConsoleMessage") -> None:
        """Store every browser console error that fires during the test."""
        if msg.type == "error":
            self._console_errors.append(msg.text)

    # ── Template Method ────────────────────────────────────────────────────────

    async def navigate(self, path: str = "") -> None:
        """
        **Template Method** — standardised navigation skeleton.

        Invariant steps (always executed in this order):

        1. Build the full URL from ``base_url + path``.
        2. ``_before_navigate()`` hook — pre-flight actions.
        3. ``page.goto()`` with ``wait_until='domcontentloaded'``.
        4. ``_after_navigate()`` hook — post-load cleanup / waits.
        5. ``_verify_loaded()`` hook — correctness assertion.

        Args:
            path: Relative URL path to append to *base_url* (e.g. ``"/search"``).
        """
        full_url = self._base_url + path
        self._logger.info(f"Navigating to {full_url}")

        await self._before_navigate()
        await self._page.goto(full_url, wait_until="domcontentloaded")
        await self._after_navigate()
        await self._verify_loaded()

    # ── Hooks (no-op defaults — subclasses override selectively) ──────────────

    async def _before_navigate(self) -> None:
        """Called before ``page.goto``.  Override for pre-flight actions."""

    async def _after_navigate(self) -> None:
        """Called after ``page.goto``.  Override to dismiss popups, wait for
        a key element to become visible, etc."""

    async def _verify_loaded(self) -> None:
        """Called last.  Override to assert the expected URL / page heading."""

    # ── Utility methods ────────────────────────────────────────────────────────

    async def take_screenshot(self, name: str) -> str:
        """
        Save a full-page screenshot to the configured screenshots directory.

        Args:
            name: Base filename *without* extension (e.g. ``"search_results"``).

        Returns:
            Absolute path of the saved ``.png`` file.
        """
        cfg = Config()
        screenshots_dir = Path(cfg.get("output_paths.screenshots", "screenshots"))
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        path = str((screenshots_dir / f"{name}.png").resolve())
        await self._page.screenshot(path=path, full_page=True)
        self._logger.info(f"Screenshot saved: {path}")
        return path

    async def get_console_errors(self) -> list[str]:
        """
        Return every browser console error captured since the page was created.

        Returns a defensive copy so callers cannot mutate the internal list.
        """
        return list(self._console_errors)
