"""
Value objects for the search flow.

All dataclasses are frozen (immutable) so they can be safely shared across
layers without risk of accidental mutation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BookSearchResult:
    """Immutable result row extracted from the search results page.

    Attributes:
        title:        Book title as displayed in the search result.
        year_text:    Raw prose text from .resultDetails, e.g.
                      "First published in 1965 in 14 editions".
                      Parse with utils.filters.parse_publish_year().
        relative_url: Path portion of the work URL, e.g. "/works/OL45804W/Dune".
        absolute_url: Full URL, e.g. "https://openlibrary.org/works/OL45804W/Dune".
    """

    title: str
    year_text: str
    relative_url: str
    absolute_url: str
