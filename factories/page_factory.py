"""
Factory Method pattern: creates Page Object instances by string name.

Decouples callers (tests, runner) from concrete page class imports.
New page types can be registered at runtime without modifying factory code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.base_page import BasePage
from pages.book_detail_page import BookDetailPage
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.reading_list_page import ReadingListPage
from pages.search_results_page import SearchResultsPage

if TYPE_CHECKING:
    from playwright.async_api import Page


class PageFactory:
    """Creates registered Page Object instances by string name.

    Usage::

        page_obj = PageFactory.create("home", playwright_page, base_url)
    """

    _registry: dict[str, type[BasePage]] = {
        "home":           HomePage,
        "search_results": SearchResultsPage,
        "book_detail":    BookDetailPage,
        "reading_list":   ReadingListPage,
        "login":          LoginPage,
    }

    @classmethod
    def create(cls, name: str, page: "Page", base_url: str) -> BasePage:
        """Instantiate the registered page object for *name*.

        Args:
            name:     Registry key (e.g. ``'home'``, ``'search_results'``).
            page:     Playwright Page instance.
            base_url: Site base URL.

        Returns:
            Constructed page object.

        Raises:
            ValueError: If *name* is not registered.
        """
        if name not in cls._registry:
            raise ValueError(
                f"Unknown page {name!r}. "
                f"Registered keys: {sorted(cls._registry)}"
            )
        return cls._registry[name](page, base_url)

    @classmethod
    def register(cls, name: str, page_class: type[BasePage]) -> None:
        """Register a new page class (open-for-extension hook).

        Args:
            name:       Key to use with :meth:`create`.
            page_class: A :class:`~pages.base_page.BasePage` subclass.
        """
        cls._registry[name] = page_class
