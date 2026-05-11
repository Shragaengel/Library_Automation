"""
Standalone async API functions for the OpenLibrary automation.

These four functions provide a flat, class-free interface that matches the
exam specification.  Each one delegates to the corresponding service class
but can be called independently with just a Playwright ``Page``.

Usage::

    from services.api import search_books, add_to_reading_list, \
                              verify_reading_list, measure_performance

    urls = await search_books(page, "lord of the rings", max_year=2000)
    results = await add_to_reading_list(page, urls)
    passed = await verify_reading_list(page, results)
    report = await measure_performance(page, "https://openlibrary.org/search?q=test")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from utils.config_loader import Config
from utils.models import Credentials

if TYPE_CHECKING:
    from playwright.async_api import Page


async def search_books(
    page: "Page",
    query: str,
    max_year: int,
    limit: int = 5,
) -> list[str]:
    """Search for books by title and return up to *limit* URLs
    whose publish year is <= *max_year*.

    Args:
        page:      Playwright Page instance.
        query:     Search term.
        max_year:  Inclusive publish-year upper bound.
        limit:     Maximum number of book URLs to return.

    Returns:
        List of absolute book-detail URLs.
    """
    from services.search_service import SearchService

    config = Config()
    service = SearchService(page, config)
    return await service.search_books_by_title_under_year(
        query=query, max_year=max_year, limit=limit,
    )


async def add_to_reading_list(
    page: "Page",
    urls: list[str],
    strategy_name: str = "random",
) -> list[dict]:
    """Log in and add each book URL to the reading list.

    Args:
        page:           Playwright Page instance.
        urls:           Absolute URLs of book detail pages.
        strategy_name:  ``"want-to-read"`` or ``"random"`` (default).

    Returns:
        List of result dicts with keys: url, action, screenshot_path,
        timestamp, error.
    """
    from services.reading_list_service import ReadingListService
    from strategies.reading_strategy import (
        RandomReadingStrategy,
        WantToReadStrategy,
    )

    config = Config()
    creds = Credentials(username=config.username, password=config.password)
    strategy = (
        WantToReadStrategy()
        if strategy_name == "want-to-read"
        else RandomReadingStrategy()
    )
    service = ReadingListService(
        page=page,
        base_url=config.base_url,
        credentials=creds,
        strategy=strategy,
    )
    await service.add_books_to_reading_list(urls)
    return service.last_add_results


async def verify_reading_list(
    page: "Page",
    add_results: list[dict],
) -> bool:
    """Verify that every shelf's book count matches what was added.

    Checks each shelf (want-to-read, already-read, currently-reading) that
    received books and asserts the count equals the number added.

    Args:
        page:         Playwright Page instance.
        add_results:  Result dicts returned by :func:`add_to_reading_list`.

    Returns:
        ``True`` if all shelves match; ``False`` otherwise.
    """
    from services.reading_list_service import ReadingListService
    from strategies.reading_strategy import WantToReadStrategy

    config = Config()
    creds = Credentials(username=config.username, password=config.password)
    service = ReadingListService(
        page=page,
        base_url=config.base_url,
        credentials=creds,
        strategy=WantToReadStrategy(),  # strategy irrelevant for counting
    )

    added = [r for r in add_results if r["error"] is None]
    if not added:
        return False

    shelves = {
        "want-to-read": len([r for r in added if r["action"] == "want-to-read"]),
        "already-read": len([r for r in added if r["action"] == "already-read"]),
        "currently-reading": len([r for r in added if r["action"] == "currently-reading"]),
    }

    all_passed = True
    for shelf, expected in shelves.items():
        if expected == 0:
            continue
        try:
            await service.assert_reading_list_count(expected, shelf=shelf)
        except AssertionError:
            all_passed = False

    return all_passed


async def measure_performance(
    page: "Page",
    url: str,
    threshold_ms: int = 3000,
) -> dict:
    """Navigate to *url*, measure page-load metrics, and return results.

    Args:
        page:          Playwright Page instance.
        url:           Full URL to measure.
        threshold_ms:  Warn if load time exceeds this value.

    Returns:
        Dict with load_time_ms, passed, and raw metrics.
    """
    from services.performance_service import PerformanceService

    config = Config()
    service = PerformanceService(page, config)
    return await service.measure_page_performance(url, threshold_ms)
