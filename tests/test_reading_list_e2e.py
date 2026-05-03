"""
End-to-end tests for the reading-list flow (Exam Task 2 + 3).

Requires a live browser AND valid credentials in .env:
    OPENLIBRARY_USER=<email>
    OPENLIBRARY_PASS=<password>

Run with:
    pytest tests/test_reading_list_e2e.py -v -m e2e

Tests are skipped automatically when credentials are missing.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.reading_list_service import ReadingListService
from services.search_service import SearchService
from strategies.reading_strategy import RandomReadingStrategy, WantToReadStrategy
from utils.models import Credentials


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_credentials() -> Credentials | None:
    user = os.getenv("OPENLIBRARY_USER")
    pwd = os.getenv("OPENLIBRARY_PASS")
    if not user or not pwd:
        return None
    return Credentials(username=user, password=pwd)


def _require_creds() -> Credentials:
    creds = _get_credentials()
    if creds is None:
        pytest.skip("OPENLIBRARY_USER / OPENLIBRARY_PASS not set in .env")
    return creds


# ══════════════════════════════════════════════════════════════════════════════
# Task 2: add_books_to_reading_list
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.reading_list
class TestAddBooksToReadingList:

    async def test_add_single_book_returns_result(self, page, config):
        """Adding a single book returns one result dict with no error."""
        creds = _require_creds()

        search = SearchService(page, config)
        books = await search.search_books_by_title_under_year(
            query="Dune", max_year=1990, limit=1
        )
        assert books, "Search returned no results — check connectivity"

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
        )
        results = await service.add_books_to_reading_list(
            [books[0].absolute_url]
        )

        assert len(results) == 1
        r = results[0]
        assert r["url"] == books[0].absolute_url
        assert r["action"] == "want-to-read"
        assert r["error"] is None

    async def test_screenshot_saved_per_book(self, page, config):
        """A screenshot file is created for each processed book."""
        creds = _require_creds()

        search = SearchService(page, config)
        books = await search.search_books_by_title_under_year(
            query="Dune", max_year=1990, limit=2
        )
        assert books, "Search returned no results"

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
            screenshots_dir="screenshots",
        )
        results = await service.add_books_to_reading_list(
            [b.absolute_url for b in books[:2]]
        )

        for r in results:
            if r["error"] is None:
                assert Path(r["screenshot_path"]).exists(), (
                    f"Missing screenshot: {r['screenshot_path']}"
                )

    async def test_random_strategy_with_seed(self, page, config):
        """RandomReadingStrategy with fixed seed is deterministic and succeeds."""
        creds = _require_creds()

        search = SearchService(page, config)
        books = await search.search_books_by_title_under_year(
            query="Dune", max_year=1990, limit=2
        )
        assert books, "Search returned no results"

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=RandomReadingStrategy(seed=1),
        )
        results = await service.add_books_to_reading_list(
            [b.absolute_url for b in books[:2]]
        )

        assert len(results) == len(books[:2])
        for r in results:
            assert r["action"] in ("want-to-read", "already-read", None)

    async def test_result_structure(self, page, config):
        """Every result dict contains all required keys."""
        creds = _require_creds()

        search = SearchService(page, config)
        books = await search.search_books_by_title_under_year(
            query="Dune", max_year=1990, limit=1
        )
        assert books

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
        )
        results = await service.add_books_to_reading_list(
            [books[0].absolute_url]
        )

        required_keys = {"url", "action", "screenshot_path", "timestamp", "error"}
        for r in results:
            assert required_keys == set(r.keys()), f"Missing keys in: {r}"


# ══════════════════════════════════════════════════════════════════════════════
# Task 3: assert_reading_list_count
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
@pytest.mark.reading_list
class TestAssertReadingListCount:

    async def test_get_reading_list_count_returns_int(self, page, config):
        """get_reading_list_count() returns a non-negative integer."""
        creds = _require_creds()

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
        )
        # Login required to see the reading list
        await service._ensure_logged_in()

        count = await service.get_reading_list_count()
        assert isinstance(count, int)
        assert count >= 0

    async def test_assert_count_passes_when_correct(self, page, config):
        """assert_reading_list_count() does not raise when count matches."""
        creds = _require_creds()

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
        )
        await service._ensure_logged_in()

        actual = await service.get_reading_list_count()
        # Should not raise
        await service.assert_reading_list_count(actual)

    async def test_assert_count_raises_when_wrong(self, page, config):
        """assert_reading_list_count() raises AssertionError on mismatch."""
        creds = _require_creds()

        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
        )
        await service._ensure_logged_in()

        actual = await service.get_reading_list_count()
        wrong = actual + 9999

        with pytest.raises(AssertionError, match="count mismatch"):
            await service.assert_reading_list_count(wrong)
