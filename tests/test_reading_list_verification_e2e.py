"""
E2E test: full flow combining Tasks 1 + 2 + 3.

Searches for books → adds them → verifies reading list count.

Run with:
    pytest tests/test_reading_list_verification_e2e.py -v -m e2e
"""

from __future__ import annotations

import os

import pytest

from services.reading_list_service import ReadingListService
from services.search_service import SearchService
from strategies.reading_strategy import WantToReadStrategy
from utils.models import Credentials

pytestmark = [pytest.mark.asyncio, pytest.mark.e2e, pytest.mark.requires_auth]


def _creds() -> Credentials | None:
    u = os.getenv("OPENLIBRARY_USER")
    p = os.getenv("OPENLIBRARY_PASS")
    return Credentials(username=u, password=p) if u and p else None


class TestFullFlowVerification:

    async def test_search_add_verify(self, page, config):
        """Full flow combining Tasks 1 + 2 + 3.

        1. Search for 'Dune', max_year=1990, limit=3.
        2. Add books using WantToReadStrategy (deterministic — no random).
        3. Verify that the reading list count is at least the number added.
        """
        creds = _creds()
        if not creds:
            pytest.skip("OPENLIBRARY_USER / OPENLIBRARY_PASS not set in .env")

        # ── Task 1: Search ────────────────────────────────────────────────
        search = SearchService(page, config)
        books = await search.search_books_by_title_under_year(
            query="Dune", max_year=1990, limit=3,
        )
        assert len(books) >= 1, "Search returned no books — check connectivity"
        urls = [b.absolute_url for b in books]

        # ── Task 2: Add ───────────────────────────────────────────────────
        service = ReadingListService(
            page=page,
            base_url=config.base_url,
            credentials=creds,
            strategy=WantToReadStrategy(),
        )
        results = await service.add_books_to_reading_list(urls)
        successes = [r for r in results if r["error"] is None]
        assert len(successes) >= 1, (
            f"No books were added successfully. Errors: "
            f"{[r['error'] for r in results]}"
        )

        # ── Task 3: Verify ────────────────────────────────────────────────
        actual_count = await service.get_reading_list_count()
        assert actual_count >= len(successes), (
            f"Expected at least {len(successes)} books in list, got {actual_count}"
        )
