"""
Centralised logger factory for the OpenLibrary automation suite.

Usage:
    from utils.logger import get_logger
    log = get_logger(__name__)
    log.info("Browser launched")
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ── Constants ─────────────────────────────────────────────────────────────────
_LOG_FORMAT  = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_FILE    = Path(__file__).resolve().parent.parent / "reports" / "automation.log"
_MAX_BYTES   = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 3                 # keep last 3 rotated files


class _SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that replaces unencodable characters instead of raising.

    On Windows the default console encoding (e.g. cp1255) cannot represent
    all Unicode characters.  The base ``StreamHandler.emit()`` catches
    ``UnicodeEncodeError`` internally and prints a ``--- Logging error ---``
    traceback *before* our code can intercept it.  To avoid this, we
    override ``emit()`` completely: format the record, encode it safely,
    and write the safe string to the stream ourselves.
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            stream = self.stream
            enc = getattr(stream, "encoding", None) or "utf-8"
            # Encode with 'replace' so unencodable chars become '?' instead
            # of raising UnicodeEncodeError
            safe = msg.encode(enc, errors="replace").decode(enc)
            stream.write(safe + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


def _resolve_level() -> int:
    """
    Read the log level from the Config singleton if available.
    Falls back to INFO so the logger can be used before Config is initialised.
    """
    try:
        from utils.config_loader import Config  # local import avoids circular deps
        level_str = Config().log_level
    except Exception:
        level_str = "INFO"
    return getattr(logging, level_str, logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """
    Return a configured :class:`logging.Logger` for *name*.

    Handlers are added only once per logger name, so calling this function
    multiple times with the same *name* is safe (no duplicate log lines).

    Output destinations:
    - **stdout** — for CI / terminal visibility.
    - **Rotating file** — ``reports/automation.log`` (5 MB × 3 backups).

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A ready-to-use :class:`logging.Logger`.
    """
    logger = logging.getLogger(name)

    # Already configured — return as-is to avoid duplicate handlers.
    if logger.handlers:
        return logger

    level = _resolve_level()
    logger.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # ── stdout handler ────────────────────────────────────────────────
    stream_handler = _SafeStreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(level)

    # ── rotating file handler ─────────────────────────────────────────
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        filename=_LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    # Prevent log records from bubbling up to the root logger (avoids
    # double-printing when pytest captures root-logger output).
    logger.propagate = False

    return logger
