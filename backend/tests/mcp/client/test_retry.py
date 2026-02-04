"""Tests for retry logic in the MCP client."""
import asyncio
from unittest.mock import MagicMock, patch

import httpx
import pytest
from tenacity import RetryError

from app.mcp.client.retry import (
    RETRYABLE_EXCEPTIONS,
    RETRYABLE_STATUS_CODES,
    RetriableHTTPError,
    create_retry_decorator,
    is_retriable_status,
)


class TestRetriableStatusCodes:
    """Test RETRYABLE_STATUS_CODES and is_retriable_status()."""

    def test_retryable_status_codes_defined(self):
        """RETRYABLE_STATUS_CODES should contain expected values."""
        assert 429 in RETRYABLE_STATUS_CODES  # Rate limit
        assert 500 in RETRYABLE_STATUS_CODES  # Internal server error
        assert 502 in RETRYABLE_STATUS_CODES  # Bad gateway
        assert 503 in RETRYABLE_STATUS_CODES  # Service unavailable
        assert 504 in RETRYABLE_STATUS_CODES  # Gateway timeout

    def test_non_retryable_status_codes(self):
        """Non-retryable status codes should not be in set."""
        assert 200 not in RETRYABLE_STATUS_CODES  # Success
        assert 201 not in RETRYABLE_STATUS_CODES  # Created
        assert 400 not in RETRYABLE_STATUS_CODES  # Bad request
        assert 401 not in RETRYABLE_STATUS_CODES  # Unauthorized
        assert 403 not in RETRYABLE_STATUS_CODES  # Forbidden
        assert 404 not in RETRYABLE_STATUS_CODES  # Not found
        assert 422 not in RETRYABLE_STATUS_CODES  # Unprocessable entity

    def test_is_retriable_status_true(self):
        """is_retriable_status should return True for retriable codes."""
        assert is_retriable_status(429) is True
        assert is_retriable_status(500) is True
        assert is_retriable_status(502) is True
        assert is_retriable_status(503) is True
        assert is_retriable_status(504) is True

    def test_is_retriable_status_false(self):
        """is_retriable_status should return False for non-retriable codes."""
        assert is_retriable_status(200) is False
        assert is_retriable_status(401) is False
        assert is_retriable_status(403) is False
        assert is_retriable_status(404) is False
        assert is_retriable_status(422) is False


class TestRetryableExceptions:
    """Test RETRYABLE_EXCEPTIONS tuple."""

    def test_retryable_exceptions_defined(self):
        """RETRYABLE_EXCEPTIONS should contain expected httpx exceptions."""
        assert httpx.ConnectError in RETRYABLE_EXCEPTIONS
        assert httpx.ConnectTimeout in RETRYABLE_EXCEPTIONS
        assert httpx.ReadTimeout in RETRYABLE_EXCEPTIONS
        assert httpx.WriteTimeout in RETRYABLE_EXCEPTIONS
        assert httpx.PoolTimeout in RETRYABLE_EXCEPTIONS


class TestRetriableHTTPError:
    """Test RetriableHTTPError exception."""

    def test_retriable_http_error_stores_response(self):
        """RetriableHTTPError should store the response object."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 503
        error = RetriableHTTPError(response)
        assert error.response is response
        assert error.status_code == 503

    def test_retriable_http_error_message(self):
        """RetriableHTTPError should have descriptive message."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 503
        error = RetriableHTTPError(response)
        assert "503" in str(error)


class TestCreateRetryDecorator:
    """Test create_retry_decorator function."""

    def test_create_decorator_with_defaults(self):
        """create_retry_decorator should return a valid decorator."""
        decorator = create_retry_decorator()
        assert callable(decorator)

    def test_create_decorator_with_custom_params(self):
        """create_retry_decorator should accept custom parameters."""
        decorator = create_retry_decorator(
            max_retries=5,
            initial_wait=0.5,
            max_wait=10.0,
            jitter=0.5,
        )
        assert callable(decorator)

    @pytest.mark.asyncio
    async def test_decorator_retries_on_retryable_exception(self):
        """Decorator should retry on RETRYABLE_EXCEPTIONS."""
        call_count = 0

        @create_retry_decorator(max_retries=3, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection failed")
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_decorator_retries_on_retriable_http_error(self):
        """Decorator should retry on RetriableHTTPError."""
        call_count = 0

        @create_retry_decorator(max_retries=3, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = MagicMock(spec=httpx.Response)
                response.status_code = 503
                raise RetriableHTTPError(response)
            return "success"

        result = await failing_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_decorator_stops_after_max_retries(self):
        """Decorator should stop retrying after max_retries."""
        call_count = 0

        @create_retry_decorator(max_retries=2, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectTimeout("Timeout")

        with pytest.raises(httpx.ConnectTimeout):
            await always_fails()

        assert call_count == 3  # 1 initial + 2 retries

    @pytest.mark.asyncio
    async def test_decorator_no_retry_on_non_retryable(self):
        """Decorator should not retry on non-retryable exceptions."""
        call_count = 0

        @create_retry_decorator(max_retries=3, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            await raises_value_error()

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Decorator should use exponential backoff (approximate check)."""
        call_count = 0
        call_times = []

        @create_retry_decorator(max_retries=2, initial_wait=0.05, max_wait=1.0, jitter=0)
        async def failing_function():
            nonlocal call_count
            call_times.append(asyncio.get_event_loop().time())
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection failed")
            return "success"

        await failing_function()

        # Check that delays between calls increase
        assert len(call_times) == 3
        delay1 = call_times[1] - call_times[0]
        delay2 = call_times[2] - call_times[1]

        # First delay should be around initial_wait (0.05s)
        assert 0.04 <= delay1 <= 0.15

        # Second delay should be longer (exponential)
        assert delay2 >= delay1 * 0.9  # Allow some tolerance


class TestRetryWithDifferentExceptions:
    """Test retry behavior with different exception types."""

    @pytest.mark.asyncio
    async def test_retry_on_connect_error(self):
        """Should retry on ConnectError."""
        call_count = 0

        @create_retry_decorator(max_retries=1, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Failed")
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_read_timeout(self):
        """Should retry on ReadTimeout."""
        call_count = 0

        @create_retry_decorator(max_retries=1, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ReadTimeout("Timeout")
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_pool_timeout(self):
        """Should retry on PoolTimeout."""
        call_count = 0

        @create_retry_decorator(max_retries=1, initial_wait=0.01, max_wait=0.1, jitter=0)
        async def func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.PoolTimeout("Pool exhausted")
            return "ok"

        result = await func()
        assert result == "ok"
        assert call_count == 2
