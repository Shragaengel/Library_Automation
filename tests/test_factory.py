"""
Unit tests for factories/page_factory.py.

No browser required — uses MagicMock in place of Playwright Page.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from factories.page_factory import PageFactory
from pages.base_page import BasePage
from pages.book_detail_page import BookDetailPage
from pages.home_page import HomePage
from pages.login_page import LoginPage
from pages.reading_list_page import ReadingListPage
from pages.search_results_page import SearchResultsPage


def _mock_page() -> MagicMock:
    return MagicMock()


class TestPageFactory:

    def test_creates_home_page(self):
        obj = PageFactory.create("home", _mock_page(), "https://example.com")
        assert isinstance(obj, HomePage)

    def test_creates_login_page(self):
        obj = PageFactory.create("login", _mock_page(), "https://example.com")
        assert isinstance(obj, LoginPage)

    def test_creates_search_results_page(self):
        obj = PageFactory.create("search_results", _mock_page(), "https://example.com")
        assert isinstance(obj, SearchResultsPage)

    def test_creates_book_detail_page(self):
        obj = PageFactory.create("book_detail", _mock_page(), "https://example.com")
        assert isinstance(obj, BookDetailPage)

    def test_creates_reading_list_page(self):
        obj = PageFactory.create("reading_list", _mock_page(), "https://example.com")
        assert isinstance(obj, ReadingListPage)

    def test_raises_value_error_on_unknown_name(self):
        with pytest.raises(ValueError, match="Unknown page"):
            PageFactory.create("nonexistent", _mock_page(), "https://example.com")

    def test_error_message_lists_registered_keys(self):
        with pytest.raises(ValueError, match="home"):
            PageFactory.create("bogus", _mock_page(), "https://example.com")

    def test_register_custom_page_class(self):
        class CustomPage(BasePage):
            pass

        PageFactory.register("custom_test_page", CustomPage)
        obj = PageFactory.create("custom_test_page", _mock_page(), "https://example.com")
        assert isinstance(obj, CustomPage)

    def test_all_default_pages_create_without_error(self):
        for name in ("home", "search_results", "book_detail", "reading_list", "login"):
            obj = PageFactory.create(name, _mock_page(), "https://example.com")
            assert obj is not None, f"Factory returned None for {name!r}"

    def test_returned_objects_are_base_page_subclasses(self):
        for name in ("home", "search_results", "book_detail", "reading_list", "login"):
            obj = PageFactory.create(name, _mock_page(), "https://example.com")
            assert isinstance(obj, BasePage), (
                f"{name!r} did not return a BasePage subclass"
            )
