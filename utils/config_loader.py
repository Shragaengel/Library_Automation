"""
Configuration loader for the OpenLibrary automation suite.

Implements the Singleton design pattern: the YAML file and .env are read
exactly once.  All subsequent Config() calls return the same instance.

Usage:
    cfg = Config()
    url  = cfg.base_url
    ms   = cfg.get("performance_thresholds.search_page_ms")
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from utils.exceptions import ConfigError

# ── Paths ──────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH  = _PROJECT_ROOT / "config.yaml"
_ENV_PATH     = _PROJECT_ROOT / ".env"

# ── Singleton guard ────────────────────────────────────────────────────────────
_HTTP_RE = re.compile(r"^https?://", re.IGNORECASE)


class Config:
    """
    Singleton configuration object.

    Loads ``config.yaml`` and merges environment variables from ``.env``
    on first instantiation.  Subsequent calls return the cached instance.
    """

    _instance: Config | None = None

    # ------------------------------------------------------------------
    # Singleton constructor
    # ------------------------------------------------------------------
    def __new__(cls, config_path: Path = _CONFIG_PATH) -> "Config":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instance = instance
        return cls._instance

    def __init__(self, config_path: Path = _CONFIG_PATH) -> None:
        # Guard: only run initialisation once.
        if self._initialized:  # type: ignore[has-type]
            return

        # Load .env first so os.environ is populated before we validate.
        if _ENV_PATH.exists():
            load_dotenv(_ENV_PATH)

        self._data: dict[str, Any] = self._load_yaml(config_path)
        self._validate()
        self._initialized = True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        """Read and parse the YAML config file."""
        if not path.exists():
            raise ConfigError(f"Config file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        if not isinstance(data, dict):
            raise ConfigError(f"Config file is malformed (expected a mapping): {path}")
        return data

    def _validate(self) -> None:
        """Validate required keys and value constraints."""
        # base_url must be present and a valid http(s) URL
        base_url = self._data.get("base_url", "")
        if not base_url:
            raise ConfigError("'base_url' is required in config.yaml")
        if not _HTTP_RE.match(str(base_url)):
            raise ConfigError(f"'base_url' must start with http:// or https://, got: {base_url!r}")

        # performance_thresholds must be a dict of positive ints
        thresholds = self._data.get("performance_thresholds", {})
        if not isinstance(thresholds, dict):
            raise ConfigError("'performance_thresholds' must be a mapping")
        for key, value in thresholds.items():
            if not isinstance(value, int) or value <= 0:
                raise ConfigError(
                    f"performance_thresholds.{key} must be a positive integer, got: {value!r}"
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get(self, dotted_path: str, default: Any = None) -> Any:
        """
        Retrieve a nested config value using dot notation.

        Example::

            cfg.get("performance_thresholds.search_page_ms")  # -> 3000
            cfg.get("browser.headless")                        # -> True
            cfg.get("missing.key", default="fallback")        # -> "fallback"
        """
        keys = dotted_path.split(".")
        node: Any = self._data
        for key in keys:
            if not isinstance(node, dict) or key not in node:
                return default
            node = node[key]
        return node

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def base_url(self) -> str:
        """Base URL of the OpenLibrary site."""
        return str(self._data["base_url"])

    @property
    def username(self) -> str:
        """OpenLibrary login e-mail, loaded from the .env file."""
        value = os.environ.get("OPENLIBRARY_USER", "")
        if not value:
            raise ConfigError("OPENLIBRARY_USER is not set in the .env file")
        return value

    @property
    def password(self) -> str:
        """OpenLibrary password, loaded from the .env file."""
        value = os.environ.get("OPENLIBRARY_PASS", "")
        if not value:
            raise ConfigError("OPENLIBRARY_PASS is not set in the .env file")
        return value

    @property
    def env_name(self) -> str:
        """Target environment name (dev / staging / prod)."""
        return os.environ.get("ENV", "dev")

    @property
    def browser_headless(self) -> bool:
        """Whether to launch the browser in headless mode."""
        return bool(self.get("browser.headless", True))

    @property
    def browser_timeout_ms(self) -> int:
        """Default Playwright timeout in milliseconds."""
        return int(self.get("browser.default_timeout_ms", 30_000))

    @property
    def performance_thresholds(self) -> dict[str, int]:
        """Dict mapping page names to their millisecond thresholds."""
        return dict(self._data.get("performance_thresholds", {}))

    @property
    def browser_slow_mo_ms(self) -> int:
        """Milliseconds of artificial delay added between Playwright actions."""
        return int(self.get("browser.slow_mo_ms", 0))

    @property
    def log_level(self) -> str:
        """Logging level string (DEBUG / INFO / WARNING / ERROR)."""
        return str(self.get("log_level", "INFO")).upper()

    # ------------------------------------------------------------------
    # Singleton reset (test-only helper)
    # ------------------------------------------------------------------
    @classmethod
    def _reset(cls) -> None:
        """
        Destroy the cached singleton instance.

        **For use in unit tests only** — never call this in production code.
        """
        cls._instance = None
