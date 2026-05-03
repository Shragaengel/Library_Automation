"""
Unit tests for the Config Singleton (utils/config_loader.py).

Tests verify:
- Two Config() calls return the exact same object.
- .get() resolves nested dotted paths correctly.
- ConfigError is raised when the config file is missing.
- ConfigError is raised when base_url is absent.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from utils.config_loader import Config
from utils.exceptions import ConfigError


@pytest.fixture(autouse=True)
def reset_singleton():
    """Destroy the singleton before and after every test for isolation."""
    Config._reset()
    yield
    Config._reset()


# ── Singleton identity ─────────────────────────────────────────────────────────

def test_singleton_returns_same_instance():
    """Two Config() calls must return the identical object (same id)."""
    a = Config()
    b = Config()
    assert a is b, "Config() should return the same singleton instance"


def test_singleton_id_is_stable():
    """id() of the instance must not change across multiple calls."""
    ids = {id(Config()) for _ in range(5)}
    assert len(ids) == 1, "Config singleton id changed between calls"


# ── .get() nested access ───────────────────────────────────────────────────────

def test_get_top_level_key():
    assert Config().get("base_url") == "https://openlibrary.org"


def test_get_nested_key():
    value = Config().get("performance_thresholds.search_page_ms")
    assert value == 3000


def test_get_second_level_nested():
    value = Config().get("browser.default_timeout_ms")
    assert value == 30_000


def test_get_missing_key_returns_default():
    result = Config().get("does.not.exist", default="fallback")
    assert result == "fallback"


def test_get_missing_key_returns_none_by_default():
    assert Config().get("no.such.key") is None


# ── Explicit properties ────────────────────────────────────────────────────────

def test_base_url_property():
    assert Config().base_url == "https://openlibrary.org"


def test_performance_thresholds_property():
    thresholds = Config().performance_thresholds
    assert isinstance(thresholds, dict)
    assert thresholds["search_page_ms"] == 3000
    assert thresholds["book_page_ms"] == 2500
    assert thresholds["reading_list_ms"] == 2000


def test_browser_headless_property():
    assert Config().browser_headless is True


def test_browser_timeout_ms_property():
    assert Config().browser_timeout_ms == 30_000


# ── ConfigError on bad / missing file ─────────────────────────────────────────

def test_config_error_when_file_missing():
    """ConfigError must be raised if the YAML file does not exist."""
    with pytest.raises(ConfigError, match="Config file not found"):
        Config(config_path=Path("/nonexistent/path/config.yaml"))


def test_config_error_when_base_url_missing(tmp_path):
    """ConfigError must be raised if base_url is not present in the YAML."""
    bad_yaml = tmp_path / "config.yaml"
    bad_yaml.write_text(
        "performance_thresholds:\n  search_page_ms: 3000\n  book_page_ms: 2500\n  reading_list_ms: 2000\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="base_url"):
        Config(config_path=bad_yaml)


def test_config_error_when_base_url_invalid(tmp_path):
    """ConfigError must be raised if base_url is not an http(s) URL."""
    bad_yaml = tmp_path / "config.yaml"
    bad_yaml.write_text(
        "base_url: 'ftp://example.com'\n"
        "performance_thresholds:\n  search_page_ms: 3000\n  book_page_ms: 2500\n  reading_list_ms: 2000\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="base_url"):
        Config(config_path=bad_yaml)


def test_config_error_when_threshold_not_positive(tmp_path):
    """ConfigError must be raised if a threshold value is not a positive int."""
    bad_yaml = tmp_path / "config.yaml"
    bad_yaml.write_text(
        "base_url: 'https://openlibrary.org'\n"
        "performance_thresholds:\n  search_page_ms: -1\n  book_page_ms: 2500\n  reading_list_ms: 2000\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="search_page_ms"):
        Config(config_path=bad_yaml)
