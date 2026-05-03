"""
Unit tests for utils/filters.py.

All tests are fully offline — no Playwright, no browser, no network.
"""

from __future__ import annotations

import pytest

from pages.models import BookSearchResult
from utils.filters import filter_books_by_year, parse_publish_year


# ── Helpers ───────────────────────────────────────────────────────────────────

def _book(year_text: str, title: str = "Test Book") -> BookSearchResult:
    return BookSearchResult(
        title=title,
        year_text=year_text,
        relative_url="/works/TEST",
        absolute_url="https://openlibrary.org/works/TEST",
    )


# ══════════════════════════════════════════════════════════════════════════════
# parse_publish_year
# ══════════════════════════════════════════════════════════════════════════════

class TestParsePublishYear:
    """Tests for the parse_publish_year() helper."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_standard_openlibrary_prose(self):
        assert parse_publish_year("First published in 1965 in 14 editions") == 1965

    def test_year_at_end(self):
        assert parse_publish_year("Published 2020") == 2020

    def test_only_year(self):
        assert parse_publish_year("1999") == 1999

    def test_year_with_surrounding_text(self):
        assert parse_publish_year("Copyright (c) 1987 by Author") == 1987

    def test_boundary_1500(self):
        assert parse_publish_year("Written in 1500") == 1500

    def test_boundary_2099(self):
        assert parse_publish_year("Projected release 2099") == 2099

    def test_year_2000(self):
        assert parse_publish_year("Year 2000 edition") == 2000

    def test_returns_first_year_when_multiple(self):
        # Should return the first match (1965), not 1987
        assert parse_publish_year("First published in 1965, reprinted in 1987") == 1965

    # ── Edge / negative cases ─────────────────────────────────────────────────

    def test_empty_string_returns_none(self):
        assert parse_publish_year("") is None

    def test_na_returns_none(self):
        assert parse_publish_year("n/a") is None

    def test_five_digit_number_returns_none(self):
        # Word boundary prevents matching inside "12345"
        assert parse_publish_year("12345") is None

    def test_year_below_1500_returns_none(self):
        assert parse_publish_year("Written in 1499") is None

    def test_year_above_2099_returns_none(self):
        assert parse_publish_year("Year 2100") is None

    def test_whitespace_only_returns_none(self):
        assert parse_publish_year("   ") is None

    def test_no_digits_returns_none(self):
        assert parse_publish_year("No year here") is None

    def test_partial_year_in_word_returns_none(self):
        # "a1965b" — no word boundary, should NOT match
        assert parse_publish_year("a1965b") is None


# ══════════════════════════════════════════════════════════════════════════════
# filter_books_by_year
# ══════════════════════════════════════════════════════════════════════════════

class TestFilterBooksByYear:
    """Tests for the filter_books_by_year() helper."""

    # ── Happy paths ───────────────────────────────────────────────────────────

    def test_keeps_books_under_max_year(self):
        books = [
            _book("First published in 1960"),
            _book("First published in 1970"),
            _book("First published in 1980"),
        ]
        result = filter_books_by_year(books, max_year=1975)
        assert len(result) == 2
        assert result[0].year_text == "First published in 1960"
        assert result[1].year_text == "First published in 1970"

    def test_includes_book_at_exact_max_year(self):
        books = [_book("First published in 1980")]
        result = filter_books_by_year(books, max_year=1980)
        assert len(result) == 1

    def test_excludes_book_one_year_over(self):
        books = [_book("First published in 1981")]
        result = filter_books_by_year(books, max_year=1980)
        assert result == []

    def test_empty_input_returns_empty(self):
        assert filter_books_by_year([], max_year=2000) == []

    def test_all_books_excluded(self):
        books = [_book("First published in 2000"), _book("First published in 2010")]
        result = filter_books_by_year(books, max_year=1990)
        assert result == []

    def test_preserves_original_order(self):
        books = [
            _book("First published in 1955", title="A"),
            _book("First published in 1945", title="B"),
            _book("First published in 1935", title="C"),
        ]
        result = filter_books_by_year(books, max_year=1960)
        assert [b.title for b in result] == ["A", "B", "C"]

    # ── Unparseable years ─────────────────────────────────────────────────────

    def test_excludes_books_with_no_year(self):
        books = [
            _book("n/a"),
            _book("First published in 1960"),
        ]
        result = filter_books_by_year(books, max_year=2000)
        assert len(result) == 1
        assert result[0].year_text == "First published in 1960"

    def test_all_unparseable_returns_empty(self):
        books = [_book("n/a"), _book(""), _book("No year")]
        result = filter_books_by_year(books, max_year=2000)
        assert result == []

    def test_does_not_mutate_input_list(self):
        original = [_book("First published in 1960"), _book("First published in 2000")]
        original_copy = list(original)
        filter_books_by_year(original, max_year=1970)
        assert original == original_copy
