"""
Retry configuration for OnCallHealth REST API client.

Uses tenacity for automatic retry with exponential backoff and jitter
to handle transient failures while preventing thundering herd.
"""
import logging
from typing import Callable, Tuple, Type

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


# Network exceptions that warrant retry (transient failures)
RETRYABLE_EXCEPTIONS: Tuple[Type[Exception], ...] = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)


# HTTP status codes that warrant retry (server overload, temporary issues)
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})


class RetriableHTTPError(Exception):
    """Raised when HTTP response has a retriable status code.

    This exception is raised for status codes in RETRYABLE_STATUS_CODES
    to trigger retry logic even when the HTTP request itself succeeded.

    Attributes:
        response: The original httpx.Response that triggered the error
        status_code: The HTTP status code for convenience
    """

    def __init__(self, response: httpx.Response):
        self.response = response
        self.status_code = response.status_code
        super().__init__(f"HTTP {response.status_code}")


def is_retriable_status(status_code: int) -> bool:
    """Check if an HTTP status code should trigger retry.

    Args:
        status_code: HTTP status code to check

    Returns:
        True if the status code is in RETRYABLE_STATUS_CODES
    """
    return status_code in RETRYABLE_STATUS_CODES


def create_retry_decorator(
    max_retries: int = 3,
    initial_wait: float = 1.0,
    max_wait: float = 30.0,
    jitter: float = 1.0,
) -> Callable:
    """Create tenacity retry decorator with exponential backoff and jitter.

    The decorator will retry on network errors (RETRYABLE_EXCEPTIONS) and
    retriable HTTP status codes (when wrapped in RetriableHTTPError).

    Jitter is added to prevent thundering herd when multiple clients
    retry simultaneously after a server recovers.

    Args:
        max_retries: Maximum number of retry attempts (excludes initial attempt)
        initial_wait: Initial wait time in seconds between retries
        max_wait: Maximum wait time in seconds between retries
        jitter: Maximum random jitter added to wait time (in seconds)

    Returns:
        Tenacity retry decorator configured with the specified parameters

    Example:
        @create_retry_decorator(max_retries=3)
        async def fetch_data():
            ...
    """
    return retry(
        stop=stop_after_attempt(max_retries + 1),  # 1 initial + max_retries
        wait=wait_exponential_jitter(initial=initial_wait, max=max_wait, jitter=jitter),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS + (RetriableHTTPError,)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
