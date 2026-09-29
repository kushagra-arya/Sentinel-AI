"""Structured JSON logging configuration for backend services."""

import logging
import sys

from pythonjsonlogger import jsonlogger


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging to emit JSON records to stdout."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s %(environment)s"
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(level.upper())


def get_logger(name: str) -> logging.Logger:
    """Return a module-scoped structured logger."""
    return logging.getLogger(name)
