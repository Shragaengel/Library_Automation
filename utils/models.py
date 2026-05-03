"""
Value objects shared across the automation suite.

All dataclasses are frozen (immutable) so they can be safely passed
between layers without risk of accidental mutation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Credentials:
    """Immutable credentials value object.

    Attributes:
        username: Email address registered with OpenLibrary.
        password: Account password. Never log or print this field.
    """

    username: str
    password: str

    def __repr__(self) -> str:
        # Mask password to prevent accidental exposure in logs / tracebacks.
        return f"Credentials(username={self.username!r}, password='***')"
