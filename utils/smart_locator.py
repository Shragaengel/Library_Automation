"""
Chain of Responsibility: resilient element-finding for Playwright pages.

Usage:
    locator = SmartLocator(page, build_default_chain())
    el = await locator.find("search button", role="button", name="Search")

Strategies are tried in order; the first one that resolves a visible element
wins.  If all strategies fail, LocatorNotFoundError is raised with a full
audit trail of what was attempted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

from utils.exceptions import LocatorNotFoundError
from utils.logger import get_logger

_log = get_logger(__name__)

# How long (ms) each strategy waits to confirm an element is visible.
_VISIBILITY_TIMEOUT_MS = 1_000


# ── Visibility helper ──────────────────────────────────────────────────────────

async def _has_visible(locator: "Locator") -> bool:
    """
    Return True if *locator* resolves to at least one visible element.

    Uses Playwright's ``wait_for(state='visible')`` with a short timeout so we
    don't block the chain for long when an element simply doesn't exist.
    """
    try:
        await locator.first.wait_for(state="visible", timeout=_VISIBILITY_TIMEOUT_MS)
        return True
    except Exception:
        return False


# ── Abstract base ──────────────────────────────────────────────────────────────

class LocatorStrategy(ABC):
    """Abstract base class for a single element-finding strategy."""

    @abstractmethod
    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        """
        Attempt to find an element using this strategy.

        Args:
            page:    The Playwright Page to search on.
            **kwargs: Strategy-specific keyword arguments (see concrete classes).

        Returns:
            A Locator if a visible element is found, else ``None``.
        """

    @property
    def name(self) -> str:
        """Human-readable strategy name used in error messages."""
        return self.__class__.__name__


# ── Concrete strategies ────────────────────────────────────────────────────────

class TestIdStrategy(LocatorStrategy):
    """Locate by ``data-testid`` attribute (most stable, prefer this)."""

    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        testid: str | None = kwargs.get("testid")
        if not testid:
            return None
        locator = page.get_by_test_id(testid)
        return locator if await _has_visible(locator) else None


class RoleStrategy(LocatorStrategy):
    """Locate by ARIA role, optionally filtered by accessible name."""

    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        role: str | None = kwargs.get("role")
        if not role:
            return None
        name: str | None = kwargs.get("name")
        locator = page.get_by_role(role, name=name) if name else page.get_by_role(role)
        return locator if await _has_visible(locator) else None


class LabelStrategy(LocatorStrategy):
    """Locate by associated ``<label>`` text (good for form inputs)."""

    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        label: str | None = kwargs.get("label")
        if not label:
            return None
        locator = page.get_by_label(label)
        return locator if await _has_visible(locator) else None


class TextStrategy(LocatorStrategy):
    """Locate by visible text content (partial match, case-sensitive)."""

    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        text: str | None = kwargs.get("text")
        if not text:
            return None
        locator = page.get_by_text(text, exact=False)
        return locator if await _has_visible(locator) else None


class CssStrategy(LocatorStrategy):
    """Locate by CSS selector — flexible but brittle; prefer semantic strategies."""

    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        css: str | None = kwargs.get("css")
        if not css:
            return None
        locator = page.locator(css)
        return locator if await _has_visible(locator) else None


class XPathStrategy(LocatorStrategy):
    """Last-resort XPath fallback — use only when no other strategy works."""

    async def try_locate(self, page: "Page", **kwargs) -> "Locator | None":
        xpath: str | None = kwargs.get("xpath")
        if not xpath:
            return None
        locator = page.locator(xpath)
        return locator if await _has_visible(locator) else None


# ── Chain builder ──────────────────────────────────────────────────────────────

def build_default_chain() -> list[LocatorStrategy]:
    """
    Return the default ordered strategy chain.

    Priority (most → least robust):
    TestId → Role → Label → Text → CSS → XPath
    """
    return [
        TestIdStrategy(),
        RoleStrategy(),
        LabelStrategy(),
        TextStrategy(),
        CssStrategy(),
        XPathStrategy(),
    ]


# ── SmartLocator ───────────────────────────────────────────────────────────────

class SmartLocator:
    """
    Chain of Responsibility orchestrator.

    Iterates the strategy chain in order and returns the first Locator that
    resolves to a visible element.  Raises LocatorNotFoundError — with a full
    audit trail — if every strategy fails.
    """

    def __init__(self, page: "Page", strategies: list[LocatorStrategy]) -> None:
        self._page = page
        self._strategies = strategies
        self._log = get_logger(self.__class__.__name__)

    async def find(self, description: str, **kwargs) -> "Locator":
        """
        Return the first Locator that resolves to a visible element.

        Args:
            description: Human-readable element label (used in error messages).
            **kwargs:    Strategy kwargs — supply the ones relevant to your element:
                         ``testid``, ``role``, ``name``, ``label``,
                         ``text``, ``css``, ``xpath``.

        Returns:
            The first successful :class:`playwright.async_api.Locator`.

        Raises:
            LocatorNotFoundError: When all strategies fail to find the element.
        """
        attempted: list[str] = []

        for strategy in self._strategies:
            try:
                locator = await strategy.try_locate(self._page, **kwargs)
                if locator is not None:
                    self._log.debug(
                        f"[{description}] resolved via {strategy.name}"
                    )
                    return locator
                # Strategy ran but found nothing (or its kwarg was absent).
                attempted.append(strategy.name)
            except Exception as exc:
                self._log.debug(
                    f"[{description}] {strategy.name} raised {exc!r}"
                )
                attempted.append(strategy.name)

        raise LocatorNotFoundError(
            f"Could not locate '{description}'. "
            f"Strategies attempted: {', '.join(attempted)}"
        )
