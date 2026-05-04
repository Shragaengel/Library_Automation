"""
Browser-native performance metric capture via the W3C Navigation Timing API.

All values are durations in milliseconds, relative to navigationStart.
Returns 0 for any metric the browser does not expose.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page


async def capture_page_metrics(page: "Page") -> dict:
    """Return performance timings captured from the browser's Performance API.

    Metrics returned:
        first_paint_ms              – Time to first pixel rendered.
        first_contentful_paint_ms   – Time to first meaningful content.
        dom_content_loaded_ms       – DOMContentLoaded event duration.
        load_time_ms                – Full page load event duration.

    Args:
        page: An already-navigated Playwright Page.

    Returns:
        Dict with the four metrics above (all int, 0 if unavailable).
    """
    return await page.evaluate("""() => {
        const nav  = performance.getEntriesByType('navigation')[0] || {};
        const paint = performance.getEntriesByType('paint');
        const fp    = paint.find(e => e.name === 'first-paint');
        const fcp   = paint.find(e => e.name === 'first-contentful-paint');

        return {
            first_paint_ms:            fp  ? Math.round(fp.startTime)  : 0,
            first_contentful_paint_ms: fcp ? Math.round(fcp.startTime) : 0,
            dom_content_loaded_ms: Math.round(
                (nav.domContentLoadedEventEnd || 0) - (nav.startTime || 0)
            ),
            load_time_ms: Math.round(
                (nav.loadEventEnd || 0) - (nav.startTime || 0)
            ),
        };
    }""")
