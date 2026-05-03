"""
End-to-end tests for the OpenLibrary book-search flow.

Requires a live internet connection and a running Playwright browser.
Run only with:  pytest tests/test_search_e2e.py -v -m e2e

All tests go through SearchService which exercises:
    HomePage → search() → SearchResultsPage → pagination → filters.py
"""

from __future__ import annotations

import pytest

from services.search_service import SearchService
from utils.config_loader import Config


# ── Fixtures ──────────────────────────────────────────────────────────────────
# `config` and `page` come from tests/conftest.py (session and function scope).


# ══════════════════════════════════════════════════════════════════════════════
# Basic search – Dune (well-known book, published 1965)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.search
class TestSearchBooksByTitleUnderYear:
    """Covers the search_books_by_title_under_year() service method."""

    async def test_returns_books_for_known_query(self, page, config: Config):
        """A well-known title returns at least one result."""
        service = SearchService(page, config)
        results = await service.search_books_by_title_under_year(
            query="Dune",
            max_year=2000,
            limit=5,
        )
        assert len(results) >= 1, "Expected at least 1 result for 'Dune' before 2000"

    async def test_result_count_capped_by_limit(self, page, config: Config):
        """Service never returns more results than the requested limit."""
        service = SearchService(page, config)
        results = await service.search_books_by_title_under_year(
            query="Dune",
            max_year=2000,
            limit=3,
        )
        assert len(results) <= 3

    async def test_all_results_have_title_and_url(self, page, config: Config):
        """Every result has a non-empty title and an absolute URL."""
        service = SearchService(page, config)
        results = await service.search_books_by_title_under_year(
            query="Dune",
            max_year=2000,
            limit=5,
        )
        for book in results:
            assert book.title, f"Empty title: {book!r}"
            assert book.absolute_url.startswith("https://"), (
                f"Bad URL: {book.absolute_url!r}"
            )

    async def test_year_filter_applied(self, page, config: Config):
        """No returned book has a parseable year above max_year."""
        from utils.filters import parse_publish_year

        service = SearchService(page, config)
        max_year = 1970
        results = await service.search_books_by_title_under_year(
            query="Dune",
            max_year=max_year,
            limit=5,
        )
        for book in results:
            year = parse_publish_year(book.year_text)
            if year is not None:
                assert year <= max_year, (
                    f"Book {book.title!r} has year {year} > {max_year}"
                )

    async def test_no_results_for_impossible_year(self, page, config: Config):
        """max_year=1500 should return an empty list (nothing published then)."""
        service = SearchService(page, config)
        results = await service.search_books_by_title_under_year(
            query="Dune",
            max_year=1500,
            limit=5,
        )
        assert results == []


# ══════════════════════════════════════════════════════════════════════════════
# Data-driven variant: multiple queries × year combinations
# ══════════════════════════════════════════════════════════════════════════════

_SEARCH_CASES = [
    ("Fantastic Mr Fox", 2000, 1),   # Classic Roald Dahl, should find ≥1
    ("Lord of the Rings", 1990, 1),  # Well-known fantasy series
    ("Harry Potter", 2005, 1),       # Popular series, post-2000 okay up to 2005
]


@pytest.mark.e2e
@pytest.mark.search
@pytest.mark.data_driven
@pytest.mark.parametrize("query,max_year,min_expected", _SEARCH_CASES)
async def test_search_parametrized(page, config, query, max_year, min_expected):
    """Data-driven: each (query, max_year) pair returns at least min_expected result."""
    service = SearchService(page, config)
    results = await service.search_books_by_title_under_year(
        query=query,
        max_year=max_year,
        limit=5,
    )
    assert len(results) >= min_expected, (
        f"Expected ≥{min_expected} result(s) for {query!r} before {max_year}, "
        f"got {len(results)}"
    )
