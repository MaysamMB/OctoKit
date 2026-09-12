"""
Centralized application logging.

Every feature and service imports `get_logger(__name__)` rather than
configuring its own handlers. Log level and directory are controlled by
core.config, not hardcoded, and the log directory is resolved via
core.paths (never the current working directory).
"""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from core.paths import get_logs_dir

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def configure_logging(level: str = "INFO", log_dir: Path | None = None) -> Path:
    """
    Configure the root application logger once. Safe to call multiple times
    (subsequent calls just update the level). Returns the log file path.
    """
    global _configured

    log_dir = log_dir or get_logs_dir()
    log_file = log_dir / "app.log"

    root = logging.getLogger("wintoolkit")
    root.setLevel(_level_to_int(level))

    if not _configured:
        formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            root.addHandler(file_handler)
        except OSError:
            # Logging must never crash the app. Fall back to console only.
            pass

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root.addHandler(console_handler)

        root.propagate = False
        _configured = True
    else:
        root.setLevel(_level_to_int(level))

    return log_file


def _level_to_int(level: str) -> int:
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }.get(level.upper(), logging.INFO)


def get_logger(name: str) -> logging.Logger:
    if not _configured:
        configure_logging()
    return logging.getLogger(f"wintoolkit.{name}")
