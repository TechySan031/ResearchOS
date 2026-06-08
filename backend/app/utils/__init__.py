"""Utility sub-package — logging, retry, text helpers, metrics."""

from app.utils.logging import configure_logging, get_logger
from app.utils.metrics import (
    ACTIVE_WORKFLOWS,
    AGENT_DURATION,
    REQUEST_COUNT,
    REQUEST_LATENCY,
    TOKENS_USED,
    setup_metrics,
)
from app.utils.retry import with_retry
from app.utils.text import (
    clean_text,
    count_tokens,
    extract_doi,
    sanitize_filename,
    truncate_text,
)

__all__ = [
    # logging
    "configure_logging",
    "get_logger",
    # metrics
    "ACTIVE_WORKFLOWS",
    "AGENT_DURATION",
    "REQUEST_COUNT",
    "REQUEST_LATENCY",
    "TOKENS_USED",
    "setup_metrics",
    # retry
    "with_retry",
    # text
    "clean_text",
    "count_tokens",
    "extract_doi",
    "sanitize_filename",
    "truncate_text",
]
