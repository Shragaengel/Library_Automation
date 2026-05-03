"""
Unit tests for the logger factory (utils/logger.py).

Tests verify:
- get_logger() returns a logging.Logger instance.
- Calling get_logger() twice with the same name does NOT add duplicate handlers.
- The logger writes to at least two handlers (stdout + file).
- Handler count stays bounded across many repeated calls.
"""

import logging

import pytest

from utils.logger import get_logger


@pytest.fixture(autouse=True)
def cleanup_loggers():
    """Remove all handlers from any logger created during the test."""
    created: list[str] = []
    yield created
    for name in created:
        logger = logging.getLogger(name)
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)


# ── Basic instantiation ────────────────────────────────────────────────────────

def test_get_logger_returns_logger_instance(cleanup_loggers):
    name = "test.basic"
    cleanup_loggers.append(name)
    logger = get_logger(name)
    assert isinstance(logger, logging.Logger)


def test_logger_has_correct_name(cleanup_loggers):
    name = "test.name_check"
    cleanup_loggers.append(name)
    logger = get_logger(name)
    assert logger.name == name


# ── Handler count (no duplicates) ─────────────────────────────────────────────

def test_no_duplicate_handlers_on_repeated_calls(cleanup_loggers):
    """Calling get_logger with the same name twice must NOT double the handlers."""
    name = "test.no_duplicates"
    cleanup_loggers.append(name)

    logger_a = get_logger(name)
    count_after_first = len(logger_a.handlers)

    logger_b = get_logger(name)
    count_after_second = len(logger_b.handlers)

    assert logger_a is logger_b, "Should be the same Logger object"
    assert count_after_first == count_after_second, (
        f"Handler count grew from {count_after_first} to {count_after_second} "
        "on the second get_logger() call — duplicate handlers added"
    )


def test_handler_count_bounded_after_many_calls(cleanup_loggers):
    """Handler count must not grow no matter how many times get_logger is called."""
    name = "test.many_calls"
    cleanup_loggers.append(name)

    first_logger = get_logger(name)
    initial_count = len(first_logger.handlers)

    for _ in range(10):
        get_logger(name)

    assert len(first_logger.handlers) == initial_count


# ── Handler types ──────────────────────────────────────────────────────────────

def test_logger_has_stream_handler(cleanup_loggers):
    """Logger must include a StreamHandler for stdout output."""
    name = "test.stream"
    cleanup_loggers.append(name)
    logger = get_logger(name)
    handler_types = [type(h) for h in logger.handlers]
    assert logging.StreamHandler in handler_types


def test_logger_has_file_handler(cleanup_loggers):
    """Logger must include a RotatingFileHandler for persistent log output."""
    from logging.handlers import RotatingFileHandler
    name = "test.file"
    cleanup_loggers.append(name)
    logger = get_logger(name)
    has_file_handler = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
    assert has_file_handler, "Expected a RotatingFileHandler but none found"


def test_logger_has_at_least_two_handlers(cleanup_loggers):
    """Logger must output to both stdout and a file — at least 2 handlers."""
    name = "test.two_handlers"
    cleanup_loggers.append(name)
    logger = get_logger(name)
    assert len(logger.handlers) >= 2


# ── Propagation ────────────────────────────────────────────────────────────────

def test_logger_does_not_propagate(cleanup_loggers):
    """propagate must be False to prevent duplicate output via the root logger."""
    name = "test.propagate"
    cleanup_loggers.append(name)
    logger = get_logger(name)
    assert logger.propagate is False
