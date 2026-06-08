"""Retry / exponential-backoff decorators built on tenacity.

Provides a single ``with_retry`` decorator that wraps any async callable
with configurable retries, jittered exponential backoff, and structured
logging of each attempt.
"""

from __future__ import annotations

import functools
from typing import Any, Callable, Sequence, Type, TypeVar

import structlog
from tenacity import (
    AsyncRetrying,
    RetryError,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.constants import DEFAULT_BACKOFF_FACTOR, DEFAULT_MAX_RETRIES

logger = structlog.stdlib.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
    retryable_exceptions: Sequence[Type[BaseException]] = (Exception,),
) -> Callable[[F], F]:
    """Decorate an async function with automatic retries and backoff.

    Args:
        max_retries: Total number of attempts (including the first).
        backoff_factor: Multiplier for the exponential wait
                        (``backoff_factor * 2^attempt`` seconds).
        retryable_exceptions: Exception types that should trigger a retry.

    Returns:
        A decorator that wraps the target coroutine.

    Example::

        @with_retry(max_retries=5, retryable_exceptions=(httpx.HTTPStatusError,))
        async def fetch_paper(url: str) -> dict: ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            try:
                async for attempt_state in AsyncRetrying(
                    stop=stop_after_attempt(max_retries),
                    wait=wait_exponential_jitter(
                        initial=backoff_factor,
                        max=60,
                        jitter=backoff_factor,
                    ),
                    retry=retry_if_exception_type(tuple(retryable_exceptions)),
                    reraise=True,
                ):
                    with attempt_state:
                        attempt += 1
                        if attempt > 1:
                            logger.warning(
                                "retry.attempt",
                                function=func.__qualname__,
                                attempt=attempt,
                                max_retries=max_retries,
                            )
                        return await func(*args, **kwargs)
            except RetryError:
                logger.error(
                    "retry.exhausted",
                    function=func.__qualname__,
                    max_retries=max_retries,
                )
                raise

        return wrapper  # type: ignore[return-value]

    return decorator
