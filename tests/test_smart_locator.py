"""
Unit tests for utils/smart_locator.py.

The Playwright Page object is replaced with a MagicMock so these tests
run without a real browser.

Scenarios covered:
- Chain returns the first strategy that succeeds.
- Chain skips strategies whose required kwarg is absent.
- Chain skips strategies that find no visible element.
- Chain raises LocatorNotFoundError when every strategy fails.
- Strategy order is respected (earlier strategies called before later ones).
- Custom strategy list works correctly.
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from utils.smart_locator import (
    CssStrategy,
    LocatorStrategy,
    RoleStrategy,
    SmartLocator,
    TestIdStrategy,
    TextStrategy,
    XPathStrategy,
    build_default_chain,
)
from utils.exceptions import LocatorNotFoundError


# ── Mock factories ─────────────────────────────────────────────────────────────

def visible_locator() -> MagicMock:
    """A mock Locator whose first element IS visible (wait_for does not raise)."""
    loc = MagicMock()
    loc.first.wait_for = AsyncMock(return_value=None)
    return loc


def invisible_locator() -> MagicMock:
    """A mock Locator whose first element is NOT visible (wait_for raises)."""
    loc = MagicMock()
    loc.first.wait_for = AsyncMock(side_effect=Exception("Timeout: not visible"))
    return loc


def make_page(
    *,
    visible: bool = True,
    testid_visible: bool | None = None,
    role_visible: bool | None = None,
    css_visible: bool | None = None,
) -> MagicMock:
    """
    Build a mock Page where each get_by_* method returns a configured locator.

    Per-method overrides (testid_visible, role_visible, css_visible) take
    precedence over the global *visible* default.
    """
    page = MagicMock()

    def _loc(override: bool | None) -> MagicMock:
        flag = override if override is not None else visible
        return visible_locator() if flag else invisible_locator()

    page.get_by_test_id.return_value = _loc(testid_visible)
    page.get_by_role.return_value    = _loc(role_visible)
    page.get_by_label.return_value   = _loc(visible)
    page.get_by_text.return_value    = _loc(visible)
    page.locator.return_value        = _loc(css_visible)
    return page


# ── Helpers ────────────────────────────────────────────────────────────────────

class _RecordingStrategy(LocatorStrategy):
    """Strategy that records every call and returns a configurable result."""

    def __init__(self, name: str, locator: MagicMock | None, call_log: list[str]) -> None:
        self._name = name
        self._locator = locator
        self._call_log = call_log

    @property
    def name(self) -> str:
        return self._name

    async def try_locate(self, page, **kwargs):
        self._call_log.append(self._name)
        return self._locator


# ── Chain success ──────────────────────────────────────────────────────────────

async def test_chain_returns_first_successful_strategy():
    """TestIdStrategy is first and visible → chain returns its locator immediately."""
    page = make_page(visible=True)
    chain = SmartLocator(page, build_default_chain())

    result = await chain.find("search input", testid="q")

    assert result is page.get_by_test_id.return_value
    page.get_by_test_id.assert_called_once_with("testid_q" if False else "q")


async def test_chain_returns_role_strategy_when_testid_missing():
    """No testid kwarg → TestIdStrategy skips → RoleStrategy finds the element."""
    page = make_page(visible=True)
    chain = SmartLocator(page, build_default_chain())

    result = await chain.find("submit button", role="button", name="Submit")

    assert result is page.get_by_role.return_value
    # TestIdStrategy must have been skipped (no testid kwarg provided).
    page.get_by_test_id.assert_not_called()


async def test_chain_falls_through_to_css_when_semantic_fail():
    """TestId + Role invisible → chain falls through to CSS."""
    page = make_page(testid_visible=False, role_visible=False, css_visible=True)
    chain = SmartLocator(page, build_default_chain())

    result = await chain.find("nav link", testid="nav", role="link", css=".nav-link")

    assert result is page.locator.return_value


# ── Strategy ordering ──────────────────────────────────────────────────────────

async def test_strategy_order_is_respected():
    """Strategies must be called in registration order; chain stops at first success."""
    call_log: list[str] = []
    loc = visible_locator()

    strategies = [
        _RecordingStrategy("first",  None, call_log),   # fails
        _RecordingStrategy("second", None, call_log),   # fails
        _RecordingStrategy("third",  loc,  call_log),   # succeeds
        _RecordingStrategy("fourth", loc,  call_log),   # should NOT be reached
    ]

    chain = SmartLocator(MagicMock(), strategies)
    result = await chain.find("some element")

    assert result is loc
    assert call_log == ["first", "second", "third"], (
        f"Expected ['first','second','third'] but got {call_log}"
    )


async def test_chain_stops_at_first_success_does_not_call_later_strategies():
    """Once a strategy succeeds, no further strategies are invoked."""
    call_log: list[str] = []
    loc = visible_locator()

    strategies = [
        _RecordingStrategy("winner", loc,  call_log),
        _RecordingStrategy("loser",  loc,  call_log),
    ]

    chain = SmartLocator(MagicMock(), strategies)
    await chain.find("button")

    assert call_log == ["winner"]


# ── Chain failure ──────────────────────────────────────────────────────────────

async def test_chain_raises_locator_not_found_when_all_fail():
    """LocatorNotFoundError is raised when every strategy returns None."""
    call_log: list[str] = []
    strategies = [
        _RecordingStrategy("alpha", None, call_log),
        _RecordingStrategy("beta",  None, call_log),
    ]

    chain = SmartLocator(MagicMock(), strategies)

    with pytest.raises(LocatorNotFoundError) as exc_info:
        await chain.find("ghost element")

    error_msg = str(exc_info.value)
    assert "ghost element" in error_msg
    assert "alpha" in error_msg
    assert "beta"  in error_msg


async def test_locator_not_found_error_includes_description():
    """Error message must contain the description passed to find()."""
    chain = SmartLocator(MagicMock(), [_RecordingStrategy("s", None, [])])

    with pytest.raises(LocatorNotFoundError, match="my unique description"):
        await chain.find("my unique description")


async def test_chain_raises_when_no_strategies_provided():
    """Empty strategy list → LocatorNotFoundError immediately."""
    chain = SmartLocator(MagicMock(), [])

    with pytest.raises(LocatorNotFoundError):
        await chain.find("anything")


# ── Individual strategies ──────────────────────────────────────────────────────

async def test_testid_strategy_skips_when_kwarg_absent():
    page = make_page(visible=True)
    result = await TestIdStrategy().try_locate(page)   # no testid kwarg
    assert result is None
    page.get_by_test_id.assert_not_called()


async def test_role_strategy_skips_when_kwarg_absent():
    page = make_page(visible=True)
    result = await RoleStrategy().try_locate(page)     # no role kwarg
    assert result is None
    page.get_by_role.assert_not_called()


async def test_css_strategy_skips_when_kwarg_absent():
    page = make_page(visible=True)
    result = await CssStrategy().try_locate(page)      # no css kwarg
    assert result is None


async def test_testid_strategy_returns_none_when_invisible():
    page = make_page(testid_visible=False)
    result = await TestIdStrategy().try_locate(page, testid="foo")
    assert result is None


async def test_testid_strategy_returns_locator_when_visible():
    page = make_page(testid_visible=True)
    result = await TestIdStrategy().try_locate(page, testid="foo")
    assert result is not None


async def test_build_default_chain_returns_six_strategies():
    chain = build_default_chain()
    assert len(chain) == 6


async def test_build_default_chain_correct_order():
    """Verify the exact type order of the default chain."""
    from utils.smart_locator import (
        LabelStrategy, XPathStrategy,
    )
    chain = build_default_chain()
    expected_types = [
        TestIdStrategy, RoleStrategy, LabelStrategy,
        TextStrategy, CssStrategy, XPathStrategy,
    ]
    for actual, expected in zip(chain, expected_types):
        assert isinstance(actual, expected), (
            f"Expected {expected.__name__}, got {type(actual).__name__}"
        )
