"""
Page Object for the OpenLibrary login page (/account/login).

IMPORTANT: The page renders TWO submit elements — the main search bar
submit AND the login-form submit.  Always use ``button[name='login']``
to target the login submit; never use ``button[type='submit']`` alone.

Selectors sourced from selectors_inventory.md (empirically verified).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pages.base_page import BasePage
from utils.exceptions import AuthenticationError

if TYPE_CHECKING:
    from playwright.async_api import Page


class LoginPage(BasePage):
    """Page Object for /account/login."""

    PATH = "/account/login"

    # ── Verified selectors (see selectors_inventory.md) ───────────────────────
    # Email input — site names it 'username' internally
    _EMAIL_CSS = "input[name='username']"
    _EMAIL_LABEL = "Email"
    _EMAIL_ID = "#username"

    # Password input
    _PASSWORD_CSS = "input[name='password']"

    # Submit — name='login' distinguishes from the search-bar submit
    _SUBMIT_CSS = "button[name='login']"
    _SUBMIT_ROLE_NAME = "Log In"

    # Error message — shown on bad credentials
    _ERROR_CSS = ".ol-signup-form__info-box.error"

    def __init__(self, page: "Page", base_url: str) -> None:
        super().__init__(page, base_url)

    # ── Template Method hooks ─────────────────────────────────────────────────

    async def _verify_loaded(self) -> None:
        """Hook: ensure the password input is visible before proceeding."""
        await self._page.locator(self._PASSWORD_CSS).wait_for(
            state="visible", timeout=10_000
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def open(self) -> None:
        """Navigate to the login page via the Template Method."""
        await self.navigate(self.PATH)

    async def login(self, username: str, password: str) -> None:
        """Fill credentials and submit the login form.

        Args:
            username: Email address registered with OpenLibrary.
            password: Account password.

        Raises:
            AuthenticationError: If an error message appears within 5 s.
        """
        self._logger.info(f"Logging in as {username!r}")

        # Fill email — primary selector, fall back to label-based
        email_loc = self._page.locator(self._EMAIL_CSS)
        if await email_loc.count() > 0:
            await email_loc.fill(username)
        else:
            await self._page.get_by_label(self._EMAIL_LABEL).fill(username)

        await self._page.locator(self._PASSWORD_CSS).fill(password)

        # Click submit — use name='login' to avoid the search-bar submit
        submit_loc = self._page.locator(self._SUBMIT_CSS)
        if await submit_loc.count() > 0:
            await submit_loc.click()
        else:
            await self._page.get_by_role("button", name=self._SUBMIT_ROLE_NAME).click()

        # Wait up to 5 s: if an error banner appears → raise; otherwise success
        error_loc = self._page.locator(self._ERROR_CSS)
        try:
            await error_loc.wait_for(state="visible", timeout=5_000)
            error_text = await error_loc.inner_text()
            raise AuthenticationError(
                f"Login failed: {error_text.strip()!r}"
            )
        except Exception as exc:
            if isinstance(exc, AuthenticationError):
                raise
            # No error banner appeared → login accepted
            self._logger.info("Login successful (no error banner appeared)")

    async def is_logged_in(self) -> bool:
        """Return True if the user appears to be logged in.

        Heuristic: the global-nav 'Log In' link is absent when logged in.
        """
        try:
            login_link = self._page.get_by_role("link", name="Log In")
            return not await login_link.is_visible(timeout=2_000)
        except Exception:
            return True  # Check failed → assume logged in
