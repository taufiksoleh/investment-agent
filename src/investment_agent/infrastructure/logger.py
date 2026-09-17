"""Structured logging setup shared by every module in the app.

Uses structlog to emit JSON so log output stays machine-parseable in any
deployment environment (container stdout, log aggregators, etc.) without each
module needing to know about formatting.
"""

import logging

import structlog


def configure_logging(level: str = "INFO") -> None:
    """Initialize structlog + stdlib logging once, at process startup."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", level=numeric_level)
    structlog.configure(
        processors=[
            # Pulls in whatever api/middleware.py bound for this request
            # (e.g. request_id) so every log line during that request carries it.
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Return a structlog logger, bound to `name` when given (typically `__name__`)."""
    return structlog.get_logger(name)
