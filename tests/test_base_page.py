"""
Unit tests for pages/base_page.py.

A lightweight concrete subclass (RecordingPage) is created inside the test
module to capture hook invocation order without touching the real browser.

Scenarios covered:
- Template Method calls hooks in the correct sequence.
- _before_navigate fires BEFORE page.goto.
- _after_navigate fires AFTER page.goto.
- _verify_loaded fires LAST.
- Default no-op hooks do not raise.
- Console error listener captures browser errors.
- take_screenshot delegates to page.screenshot and returns a path string.
- get_console_errors returns a defensive copy.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from pages.base_page import BasePage


# ── Concrete subclass for testing ──────────────────────────────────────────────

class RecordingPage(BasePage):
    """Minimal BasePage subclass that records hook call order."""

    def __init__(self, page, base_url: str = "https://example.com") -> None:
        super().__init__(page, base_url)
        self.call_order: list[str] = []
        self.goto_called_before_after: bool = False

    async def _before_navigate(self) -> None:
        self.call_order.append("before")

    async def _after_navigate(self) -> None:
        # Capture whether goto was already called when this hook runs.
        self.goto_called_before_after = self._page.goto.called
        self.call_order.append("after")

    async def _verify_loaded(self) -> None:
        self.call_order.append("verify")


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def mock_page() -> MagicMock:
    """A mock Playwright Page with async goto and screenshot methods."""
    page = MagicMock()
    page.goto = AsyncMock(return_value=None)
    page.screenshot = AsyncMock(return_value=None)
    page.on = MagicMock()        # event listener registration (sync)
    return page


@pytest.fixture()
def recording_page(mock_page) -> RecordingPage:
    return RecordingPage(mock_page, "https://example.com")


# ── Template Method hook ordering ──────────────────────────────────────────────

async def test_navigate_calls_all_hooks(recording_page):
    """All three hooks must be invoked during navigate()."""
    await recording_page.navigate("/test")
    assert "before"  in recording_page.call_order
    assert "after"   in recording_page.call_order
    assert "verify"  in recording_page.call_order


async def test_navigate_hook_order_is_correct(recording_page):
    """Hooks must fire in exactly the order: before → after → verify."""
    await recording_page.navigate("/test")
    assert recording_page.call_order == ["before", "after", "verify"]


async def test_before_navigate_fires_before_goto(recording_page):
    """_before_navigate must run before page.goto is called."""
    fired_before_goto: list[bool] = []

    async def _before():
        fired_before_goto.append(recording_page._page.goto.called)

    recording_page._before_navigate = _before
    await recording_page.navigate("/test")

    assert fired_before_goto == [False], (
        "_before_navigate was called AFTER page.goto — wrong order"
    )


async def test_after_navigate_fires_after_goto(recording_page):
    """_after_navigate must run after page.goto has been called."""
    await recording_page.navigate("/test")
    assert recording_page.goto_called_before_after is True, (
        "_after_navigate was called BEFORE page.goto — wrong order"
    )


async def test_navigate_calls_page_goto_with_correct_url(recording_page, mock_page):
    """page.goto must receive the full concatenated URL."""
    await recording_page.navigate("/search")
    mock_page.goto.assert_called_once_with(
        "https://example.com/search",
        wait_until="domcontentloaded",
    )


async def test_navigate_strips_trailing_slash_from_base_url(mock_page):
    """base_url trailing slash must not produce a double slash in the URL."""
    page = RecordingPage(mock_page, "https://example.com/")
    await page.navigate("/path")
    mock_page.goto.assert_called_once_with(
        "https://example.com/path",
        wait_until="domcontentloaded",
    )


async def test_navigate_empty_path_uses_base_url(recording_page, mock_page):
    """navigate() with no argument navigates to base_url alone."""
    await recording_page.navigate()
    mock_page.goto.assert_called_once_with(
        "https://example.com",
        wait_until="domcontentloaded",
    )


# ── Default no-op hooks ────────────────────────────────────────────────────────

async def test_default_hooks_do_not_raise(mock_page):
    """A BasePage with no hook overrides must navigate without errors."""

    class MinimalPage(BasePage):
        pass   # no overrides — all hooks are no-ops

    page = MinimalPage(mock_page, "https://example.com")
    await page.navigate("/")    # must not raise


# ── Console error capture ──────────────────────────────────────────────────────

async def test_console_errors_captured(recording_page, mock_page):
    """Console 'error' messages must be recorded by the listener."""
    # Retrieve the listener registered with page.on("console", ...)
    on_call_args = mock_page.on.call_args_list
    console_listeners = [
        args[0][1] for args in on_call_args if args[0][0] == "console"
    ]
    assert console_listeners, "No 'console' listener was registered on page.on"

    listener = console_listeners[0]

    # Simulate a browser console error.
    fake_msg = MagicMock()
    fake_msg.type = "error"
    fake_msg.text = "Uncaught TypeError: foo is not a function"
    listener(fake_msg)

    errors = await recording_page.get_console_errors()
    assert errors == ["Uncaught TypeError: foo is not a function"]


async def test_non_error_console_messages_are_ignored(recording_page, mock_page):
    """Console messages of type 'log' or 'warn' must NOT be recorded."""
    on_call_args = mock_page.on.call_args_list
    listener = [a[0][1] for a in on_call_args if a[0][0] == "console"][0]

    for msg_type in ("log", "warn", "info"):
        msg = MagicMock()
        msg.type = msg_type
        msg.text = f"a {msg_type} message"
        listener(msg)

    errors = await recording_page.get_console_errors()
    assert errors == []


async def test_get_console_errors_returns_defensive_copy(recording_page, mock_page):
    """Mutating the returned list must not affect the internal state."""
    on_call_args = mock_page.on.call_args_list
    listener = [a[0][1] for a in on_call_args if a[0][0] == "console"][0]

    err_msg = MagicMock()
    err_msg.type = "error"
    err_msg.text = "original error"
    listener(err_msg)

    errors = await recording_page.get_console_errors()
    errors.clear()   # mutate the returned copy

    # Internal list must still have the error.
    errors_again = await recording_page.get_console_errors()
    assert errors_again == ["original error"]


# ── take_screenshot ────────────────────────────────────────────────────────────

async def test_take_screenshot_returns_string_path(recording_page, mock_page, tmp_path):
    """take_screenshot must return a non-empty string path."""
    with patch("pages.base_page.Config") as mock_cfg_cls:
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = str(tmp_path)
        mock_cfg_cls.return_value = mock_cfg

        result = await recording_page.take_screenshot("test_shot")

    assert isinstance(result, str)
    assert result.endswith("test_shot.png")


async def test_take_screenshot_calls_page_screenshot(recording_page, mock_page, tmp_path):
    """page.screenshot must be called with the correct path and full_page=True."""
    with patch("pages.base_page.Config") as mock_cfg_cls:
        mock_cfg = MagicMock()
        mock_cfg.get.return_value = str(tmp_path)
        mock_cfg_cls.return_value = mock_cfg

        await recording_page.take_screenshot("my_page")

    mock_page.screenshot.assert_called_once()
    call_kwargs = mock_page.screenshot.call_args.kwargs
    assert call_kwargs.get("full_page") is True
    assert call_kwargs["path"].endswith("my_page.png")
