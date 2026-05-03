"""
Shared pytest fixtures for the OpenLibrary automation suite.

Fixture scopes
--------------
config          session  – Config singleton, loaded once per test run.
browser_context function – Fresh Playwright BrowserContext per test.
page            function – Fresh Playwright Page derived from browser_context.

All async fixtures use ``asyncio_mode = auto`` (set in pytest.ini) so there
is no need to decorate them with @pytest.mark.asyncio.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from playwright.async_api import async_playwright

from utils.config_loader import Config


# ── Sync session-scoped Config ────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config() -> Config:
    """Return the singleton Config instance for the whole test session."""
    return Config()


# ── Async browser fixtures ────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def browser_context(config: Config):
    """
    Yield a fresh Playwright BrowserContext for each test.

    Browser settings (headless, slow_mo, viewport) come from config.yaml.
    The browser and context are both closed after the test completes.
    """
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=config.browser_headless,
            slow_mo=config.browser_slow_mo_ms,
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            base_url=config.base_url,
        )
        context.set_default_timeout(config.browser_timeout_ms)
        yield context
        await context.close()
        await browser.close()


@pytest_asyncio.fixture
async def page(browser_context):
    """
    Yield a fresh Playwright Page from the browser_context fixture.

    Using a dedicated Page fixture makes individual tests simpler and keeps
    each test fully isolated (separate page ↔ separate navigation history).
    """
    pg = await browser_context.new_page()
    yield pg
    await pg.close()
