"""
Decorator that times async functions and records measurements to
PerformanceCollector.

IMPORTANT: A threshold violation logs a WARNING — it NEVER raises an exception.
The exam requirement is: threshold exceeded = warning, not failure.
"""

from __future__ import annotations

import functools
import time
from typing import Any, Callable

from utils.logger import get_logger

_logger = get_logger("performance")


def measure_performance(threshold_ms: int, page_name: str):
    """Time an async function and publish the measurement to PerformanceCollector.

    Args:
        threshold_ms: Log a WARNING (but do NOT raise) if elapsed > this.
        page_name:    Human-readable label stored in the performance report.

    Usage::

        @measure_performance(threshold_ms=3000, page_name="search_page")
        async def open_search(page, url):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                elapsed_ms = (time.perf_counter() - start) * 1000
                exceeded = elapsed_ms > threshold_ms

                if exceeded:
                    _logger.warning(
                        f"[PERF] {page_name} took {elapsed_ms:.0f}ms "
                        f"(threshold: {threshold_ms}ms) — exceeded, NOT failed"
                    )
                else:
                    _logger.info(
                        f"[PERF] {page_name} took {elapsed_ms:.0f}ms "
                        f"(threshold: {threshold_ms}ms)"
                    )

                # Import inside finally to avoid circular imports at module load
                from reporters.performance_collector import PerformanceCollector
                PerformanceCollector().record(
                    page_name=page_name,
                    duration_ms=elapsed_ms,
                    threshold_ms=threshold_ms,
                    exceeded=exceeded,
                )

        return wrapper
    return decorator
