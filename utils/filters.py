"""
Pure filter functions for search results.

No Playwright imports — this module is framework-agnostic and fully unit-testable
without a browser.  All functions are stateless and side-effect-free.
"""

from __future__ import annotations

import re

from pages.models import BookSearchResult

# Matches 4-digit years in the range 1500–2099.
# Anchored with \b so "12345" does NOT match.
_YEAR_RE = re.compile(r'\b(1[5-9]\d\d|20\d\d)\b')


def parse_publish_year(text: str) -> int | None:
    """Extract the first plausible 4-digit publish year from prose text.

    Handles the OpenLibrary year format:
    ``"First published in 1965 in 14 editions"`` → ``1965``

    Args:
        text: Raw string from ``.resultDetails`` element.

    Returns:
        Integer year if found, else ``None``.

    Examples::

        parse_publish_year("First published in 1965 in 14 editions") == 1965
        parse_publish_year("Published 2020")                          == 2020
        parse_publish_year("n/a")                                     is None
        parse_publish_year("")                                        is None
        parse_publish_year("12345")                                   is None  # 5 digits
    """
    if not text:
        return None
    match = _YEAR_RE.search(text)
    return int(match.group(1)) if match else None


def filter_books_by_year(
    books: list[BookSearchResult],
    max_year: int,
) -> list[BookSearchResult]:
    """Return only books whose parsed publish year is ≤ max_year.

    Books whose year cannot be parsed are **excluded** (the caller can log them
    separately if needed).  The original list order is preserved.

    Args:
        books:    List of raw search results.
        max_year: Inclusive upper bound on the publish year.

    Returns:
        Filtered list (may be empty).
    """
    result: list[BookSearchResult] = []
    for book in books:
        year = parse_publish_year(book.year_text)
        if year is not None and year <= max_year:
            result.append(book)
    return result
