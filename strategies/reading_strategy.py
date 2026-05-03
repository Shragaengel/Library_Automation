"""
Strategy design pattern for marking a book's reading status.

Each concrete Strategy wraps a single BookDetailPage action so callers
(ReadingListService) never depend on the concrete marking logic directly.

Strategies
----------
WantToReadStrategy       – marks as Want to Read (default shelf)
AlreadyReadStrategy      – marks as Already Read via dropdown
CurrentlyReadingStrategy – marks as Currently Reading via dropdown
RandomReadingStrategy    – randomly selects between pool strategies
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pages.book_detail_page import BookDetailPage


class ReadingStrategy(ABC):
    """Abstract Strategy: defines the interface for marking a book."""

    @abstractmethod
    async def mark(self, book_page: "BookDetailPage") -> str:
        """Mark the book using this strategy.

        Args:
            book_page: An already-opened BookDetailPage instance.

        Returns:
            A label describing the action taken, e.g. ``'want-to-read'``.
        """


class WantToReadStrategy(ReadingStrategy):
    """Marks the book as Want to Read (the default / initial shelf)."""

    async def mark(self, book_page: "BookDetailPage") -> str:
        await book_page.mark_as_want_to_read()
        return "want-to-read"


class AlreadyReadStrategy(ReadingStrategy):
    """Marks the book as Already Read via the dropdown."""

    async def mark(self, book_page: "BookDetailPage") -> str:
        await book_page.mark_as_already_read()
        return "already-read"


class CurrentlyReadingStrategy(ReadingStrategy):
    """Marks the book as Currently Reading via the dropdown."""

    async def mark(self, book_page: "BookDetailPage") -> str:
        await book_page.mark_as_currently_reading()
        return "currently-reading"


class RandomReadingStrategy(ReadingStrategy):
    """Randomly selects a strategy from a configurable pool.

    The default pool is [WantToReadStrategy, AlreadyReadStrategy].
    CurrentlyReadingStrategy is intentionally excluded from the default pool
    but can be injected via ``pool`` for broader coverage.

    Args:
        pool: Strategies to draw from. Defaults to Want + Already.
        seed: Optional integer seed for deterministic test runs.

    Examples::

        # Deterministic (same seed → same sequence every time)
        strategy = RandomReadingStrategy(seed=42)

        # Custom pool
        strategy = RandomReadingStrategy(
            pool=[WantToReadStrategy(), CurrentlyReadingStrategy()],
        )
    """

    def __init__(
        self,
        pool: list[ReadingStrategy] | None = None,
        seed: int | None = None,
    ) -> None:
        self._rng = random.Random(seed)
        self._pool: list[ReadingStrategy] = pool or [
            WantToReadStrategy(),
            AlreadyReadStrategy(),
        ]

    async def mark(self, book_page: "BookDetailPage") -> str:
        chosen = self._rng.choice(self._pool)
        return await chosen.mark(book_page)
