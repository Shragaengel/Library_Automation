"""
Standalone runner for LibraryTestRunner — called by the UI as a subprocess.

Usage:
    python ui/run_flow.py <query> <max_year> <limit>

Prints progress lines to stdout, then a final JSON line:
    RESULT:{"urls_found": 3, "urls_added": 3, ...}
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Make sure openlibrary_automation/ is on sys.path
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))


async def main(query: str, max_year: int, limit: int) -> None:
    from playwright.async_api import async_playwright
    from runner.library_test_runner import LibraryTestRunner
    from strategies.reading_strategy import WantToReadStrategy
    from utils.config_loader import Config

    config = Config()
    print(f"Starting: query={query!r}, max_year={max_year}, limit={limit}")
    print(f"Site: {config.base_url}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=config.browser_headless,
            slow_mo=config.browser_slow_mo_ms,
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
        )
        context.set_default_timeout(config.browser_timeout_ms)
        page = await context.new_page()

        runner = LibraryTestRunner(
            page=page,
            config=config,
            strategy=WantToReadStrategy(),
        )

        print("Running full flow...")
        summary = await runner.run_full_flow(
            query=query,
            max_year=max_year,
            limit=limit,
        )

        await context.close()
        await browser.close()

    # Print structured result on its own line — UI parses this
    print(f"RESULT:{json.dumps(summary)}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python run_flow.py <query> <max_year> <limit>")
        sys.exit(1)

    query   = sys.argv[1]
    max_year = int(sys.argv[2])
    limit   = int(sys.argv[3])

    asyncio.run(main(query, max_year, limit))
