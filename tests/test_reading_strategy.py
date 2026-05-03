"""
Unit tests for strategies/reading_strategy.py.

All tests are fully offline — no Playwright, no browser, no network.
AsyncMock replaces every BookDetailPage method so tests run in milliseconds.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from strategies.reading_strategy import (
    AlreadyReadStrategy,
    CurrentlyReadingStrategy,
    RandomReadingStrategy,
    WantToReadStrategy,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_book_page():
    """Return a mock BookDetailPage with async mark methods."""
    page = MagicMock()
    page.mark_as_want_to_read = AsyncMock()
    page.mark_as_already_read = AsyncMock()
    page.mark_as_currently_reading = AsyncMock()
    return page


# ══════════════════════════════════════════════════════════════════════════════
# WantToReadStrategy
# ══════════════════════════════════════════════════════════════════════════════

class TestWantToReadStrategy:

    async def test_calls_correct_method(self):
        page = _mock_book_page()
        result = await WantToReadStrategy().mark(page)
        page.mark_as_want_to_read.assert_called_once()
        page.mark_as_already_read.assert_not_called()
        page.mark_as_currently_reading.assert_not_called()

    async def test_returns_correct_label(self):
        page = _mock_book_page()
        assert await WantToReadStrategy().mark(page) == "want-to-read"


# ══════════════════════════════════════════════════════════════════════════════
# AlreadyReadStrategy
# ══════════════════════════════════════════════════════════════════════════════

class TestAlreadyReadStrategy:

    async def test_calls_correct_method(self):
        page = _mock_book_page()
        result = await AlreadyReadStrategy().mark(page)
        page.mark_as_already_read.assert_called_once()
        page.mark_as_want_to_read.assert_not_called()
        page.mark_as_currently_reading.assert_not_called()

    async def test_returns_correct_label(self):
        page = _mock_book_page()
        assert await AlreadyReadStrategy().mark(page) == "already-read"


# ══════════════════════════════════════════════════════════════════════════════
# CurrentlyReadingStrategy
# ══════════════════════════════════════════════════════════════════════════════

class TestCurrentlyReadingStrategy:

    async def test_calls_correct_method(self):
        page = _mock_book_page()
        result = await CurrentlyReadingStrategy().mark(page)
        page.mark_as_currently_reading.assert_called_once()
        page.mark_as_want_to_read.assert_not_called()
        page.mark_as_already_read.assert_not_called()

    async def test_returns_correct_label(self):
        page = _mock_book_page()
        assert await CurrentlyReadingStrategy().mark(page) == "currently-reading"


# ══════════════════════════════════════════════════════════════════════════════
# RandomReadingStrategy
# ══════════════════════════════════════════════════════════════════════════════

class TestRandomReadingStrategy:

    async def test_default_pool_only_want_and_already(self):
        """Default pool never returns 'currently-reading'."""
        strategy = RandomReadingStrategy(seed=0)
        results = set()
        for _ in range(100):
            page = _mock_book_page()
            results.add(await strategy.mark(page))
        assert results <= {"want-to-read", "already-read"}
        assert "currently-reading" not in results

    async def test_deterministic_with_seed(self):
        """Same seed produces identical sequence across two instances."""
        strategy_a = RandomReadingStrategy(seed=42)
        strategy_b = RandomReadingStrategy(seed=42)
        seq_a, seq_b = [], []
        for _ in range(20):
            seq_a.append(await strategy_a.mark(_mock_book_page()))
            seq_b.append(await strategy_b.mark(_mock_book_page()))
        assert seq_a == seq_b

    async def test_different_seeds_differ(self):
        """Different seeds produce different sequences (with overwhelming probability)."""
        async def _collect(s, n):
            return [await s.mark(_mock_book_page()) for _ in range(n)]

        seq_1 = await _collect(RandomReadingStrategy(seed=1), 20)
        seq_2 = await _collect(RandomReadingStrategy(seed=2), 20)
        # Over 20 draws from 2-item pool: P(identical) ≈ (0.5)^20 < 1e-6
        assert seq_1 != seq_2

    async def test_distribution_roughly_even(self):
        """Over 1000 draws, each label appears ~50% (±10% margin)."""
        strategy = RandomReadingStrategy()
        counts: dict[str, int] = {}
        for _ in range(1000):
            page = _mock_book_page()
            label = await strategy.mark(page)
            counts[label] = counts.get(label, 0) + 1
        assert 400 <= counts.get("want-to-read", 0) <= 600, f"Skewed: {counts}"
        assert 400 <= counts.get("already-read", 0) <= 600, f"Skewed: {counts}"

    async def test_custom_single_strategy_pool(self):
        """Pool with one strategy always picks that strategy."""
        strategy = RandomReadingStrategy(pool=[WantToReadStrategy()], seed=99)
        for _ in range(10):
            page = _mock_book_page()
            assert await strategy.mark(page) == "want-to-read"

    async def test_custom_pool_with_currently_reading(self):
        """Custom pool can include CurrentlyReadingStrategy."""
        strategy = RandomReadingStrategy(
            pool=[CurrentlyReadingStrategy()], seed=7
        )
        for _ in range(5):
            page = _mock_book_page()
            assert await strategy.mark(page) == "currently-reading"

    async def test_returns_string_label(self):
        """mark() always returns a non-empty string."""
        strategy = RandomReadingStrategy(seed=0)
        for _ in range(20):
            page = _mock_book_page()
            result = await strategy.mark(page)
            assert isinstance(result, str)
            assert len(result) > 0
