"""Integration tests for client resilience patterns."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from app.mcp.client.base import OnCallHealthClient
from app.mcp.client.circuit_breaker import CircuitBreakerOpenError
from app.mcp.client.config import ClientConfig
from app.mcp.client.exceptions import (
    AuthenticationError,
    NotFoundError,
    RateLimitError,
    ServiceUnavailableError,
)


class TestResilienceIntegrationSuccess:
    """Test successful request flow with resilience."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_successful_request_no_retry(self, respx_mock):
        """Successful request should not trigger retry."""
        call_count = 0

        def track_call(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json={"status": "ok"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=track_call
        )

        config = ClientConfig(max_retries=3)
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            response = await client.get("/api/v1/test")
            assert response.status_code == 200
            assert call_count == 1  # Only one call, no retries
        finally:
            await client.close()


class TestResilienceIntegrationRetry:
    """Test retry behavior on transient failures."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_503_then_success(self, respx_mock):
        """Should retry on 503 and succeed on subsequent request."""
        call_count = 0

        def conditional_response(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(503, json={"error": "Service unavailable"})
            return httpx.Response(200, json={"status": "ok"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=conditional_response
        )

        config = ClientConfig(
            max_retries=3,
            retry_initial_wait=0.01,
            retry_max_wait=0.1,
            retry_jitter=0,
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            response = await client.get("/api/v1/test")
            assert response.status_code == 200
            assert call_count == 2  # 1 failure + 1 success
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_500_then_success(self, respx_mock):
        """Should retry on 500 and succeed."""
        call_count = 0

        def conditional_response(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(500, json={"error": "Internal error"})
            return httpx.Response(200, json={"status": "ok"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=conditional_response
        )

        config = ClientConfig(
            max_retries=3,
            retry_initial_wait=0.01,
            retry_max_wait=0.1,
            retry_jitter=0,
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            response = await client.get("/api/v1/test")
            assert response.status_code == 200
            assert call_count == 2
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_on_429_then_success(self, respx_mock):
        """Should retry on 429 rate limit and succeed."""
        call_count = 0

        def conditional_response(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(
                    429,
                    headers={"Retry-After": "1"},
                    json={"error": "Rate limited"},
                )
            return httpx.Response(200, json={"status": "ok"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=conditional_response
        )

        config = ClientConfig(
            max_retries=3,
            retry_initial_wait=0.01,
            retry_max_wait=0.1,
            retry_jitter=0,
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            response = await client.get("/api/v1/test")
            assert response.status_code == 200
            assert call_count == 2
        finally:
            await client.close()


class TestResilienceIntegrationNoRetry:
    """Test no-retry behavior on non-retriable errors."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_401_no_retry(self, respx_mock):
        """401 should fail immediately without retry."""
        call_count = 0

        def track_call(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(401, json={"error": "Unauthorized"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=track_call
        )

        config = ClientConfig(max_retries=3)
        client = OnCallHealthClient(api_key="invalid-key", config=config)

        try:
            with pytest.raises(AuthenticationError):
                await client.get("/api/v1/test")
            assert call_count == 1  # Only one call, no retries
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_404_no_retry(self, respx_mock):
        """404 should fail immediately without retry."""
        call_count = 0

        def track_call(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(404, json={"error": "Not found"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=track_call
        )

        config = ClientConfig(max_retries=3)
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            with pytest.raises(NotFoundError):
                await client.get("/api/v1/test")
            assert call_count == 1
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_403_no_retry(self, respx_mock):
        """403 should fail immediately without retry."""
        call_count = 0

        def track_call(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(403, json={"error": "Forbidden"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/admin").mock(
            side_effect=track_call
        )

        config = ClientConfig(max_retries=3)
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            with pytest.raises(AuthenticationError):
                await client.get("/api/v1/admin")
            assert call_count == 1
        finally:
            await client.close()


class TestResilienceIntegrationCircuitBreaker:
    """Test circuit breaker behavior."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_circuit_breaker_opens_on_persistent_failure(self, respx_mock):
        """Circuit breaker should open after consecutive failures.

        When fail_max failures occur, the last failure raises CircuitBreakerOpenError
        (our wrapper around aiobreaker's CircuitBreakerError).
        """
        from app.mcp.client.retry import RetriableHTTPError

        call_count = 0

        def always_fail(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(500, json={"error": "Server error"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=always_fail
        )

        config = ClientConfig(
            max_retries=0,  # No retries for this test
            circuit_breaker_fail_max=2,  # Open after 2 failures
            circuit_breaker_timeout_seconds=30,
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            # First call fails with RetriableHTTPError (500 is retriable)
            with pytest.raises(RetriableHTTPError):
                await client.get("/api/v1/test")
            assert call_count == 1

            # Second call - fail_max reached, breaker opens and raises CircuitBreakerOpenError
            with pytest.raises(CircuitBreakerOpenError) as exc_info:
                await client.get("/api/v1/test")
            assert call_count == 2

            assert "oncallhealth-api" in str(exc_info.value)

            # Third call - breaker is open, no HTTP call made
            with pytest.raises(CircuitBreakerOpenError):
                await client.get("/api/v1/test")
            assert call_count == 2  # No additional call made
        finally:
            await client.close()

    @pytest.mark.asyncio
    @respx.mock
    async def test_circuit_breaker_recovers(self, respx_mock):
        """Circuit breaker should recover after timeout."""
        call_count = 0

        def conditional_response(request):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                return httpx.Response(500, json={"error": "Server error"})
            return httpx.Response(200, json={"status": "ok"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=conditional_response
        )

        config = ClientConfig(
            max_retries=0,
            circuit_breaker_fail_max=1,
            circuit_breaker_timeout_seconds=0.1,  # Very short timeout for testing
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            # Trip the circuit breaker (fail_max=1 means first failure opens it)
            with pytest.raises(CircuitBreakerOpenError):
                await client.get("/api/v1/test")

            # Wait for timeout
            await asyncio.sleep(0.15)

            # Should be able to make request again (half-open state)
            response = await client.get("/api/v1/test")
            assert response.status_code == 200
        finally:
            await client.close()


class TestResilienceIntegrationRetryExhaustion:
    """Test behavior when retries are exhausted."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_exhausted_retries_raises_service_unavailable(self, respx_mock):
        """Should raise after exhausting retries on 503."""
        call_count = 0

        def always_503(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(503, json={"error": "Service unavailable"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=always_503
        )

        config = ClientConfig(
            max_retries=2,  # Will try 3 times total
            retry_initial_wait=0.01,
            retry_max_wait=0.1,
            retry_jitter=0,
            circuit_breaker_fail_max=10,  # High threshold to not interfere
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            # After retries exhausted, the RetriableHTTPError should be raised
            # The circuit breaker will see this and propagate it
            from app.mcp.client.retry import RetriableHTTPError

            with pytest.raises(RetriableHTTPError):
                await client.get("/api/v1/test")

            # Should have made 3 attempts (1 initial + 2 retries)
            assert call_count == 3
        finally:
            await client.close()


class TestResilienceIntegrationHealthMonitor:
    """Test health monitor integration."""

    @pytest.mark.asyncio
    async def test_client_with_health_monitor(self):
        """Client should work with health monitor started."""
        config = ClientConfig()
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            await client.start_health_monitor(check_interval=1)
            assert client._health_monitor is not None
            assert client._health_monitor.is_running is True
        finally:
            await client.close()
            # Health monitor should be stopped after close
            assert client._health_monitor is None

    @pytest.mark.asyncio
    async def test_client_close_stops_health_monitor(self):
        """close() should stop health monitor."""
        config = ClientConfig()
        client = OnCallHealthClient(api_key="test-key", config=config)

        await client.start_health_monitor(check_interval=1)
        monitor = client._health_monitor
        assert monitor.is_running is True

        await client.close()
        assert client._health_monitor is None

    @pytest.mark.asyncio
    async def test_stop_health_monitor_explicit(self):
        """stop_health_monitor() should stop the monitor."""
        config = ClientConfig()
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            await client.start_health_monitor(check_interval=1)
            await client.stop_health_monitor()
            assert client._health_monitor is None
        finally:
            await client.close()


class TestResilienceIntegrationCombined:
    """Test combined resilience patterns."""

    @pytest.mark.asyncio
    @respx.mock
    async def test_retry_then_circuit_breaker(self, respx_mock):
        """Should retry within each request, circuit breaker counts request-level failures.

        With fail_max=2 and max_retries=1:
        - First request: 2 HTTP attempts, retries exhausted, circuit breaker counts 1 request failure
        - Second request: 2 HTTP attempts, retries exhausted, 2nd request failure trips breaker
        - Third request: breaker is open, no call made

        Note: The circuit breaker wraps the retry function, so it only sees
        one failure per request() call (the final propagated error).
        """
        from app.mcp.client.retry import RetriableHTTPError

        call_count = 0

        def always_fail(request):
            nonlocal call_count
            call_count += 1
            return httpx.Response(503, json={"error": "Service unavailable"})

        respx_mock.get("https://api.oncallhealth.ai/api/v1/test").mock(
            side_effect=always_fail
        )

        config = ClientConfig(
            max_retries=1,  # 2 total HTTP attempts per request
            retry_initial_wait=0.01,
            retry_max_wait=0.1,
            retry_jitter=0,
            circuit_breaker_fail_max=2,  # Open after 2 request-level failures
            circuit_breaker_timeout_seconds=30,
        )
        client = OnCallHealthClient(api_key="test-key", config=config)

        try:
            # First request: 2 HTTP attempts, retries exhausted, 1st request failure
            with pytest.raises(RetriableHTTPError):
                await client.get("/api/v1/test")
            assert call_count == 2

            # Second request: 2 HTTP attempts, 2nd request failure trips breaker
            with pytest.raises(CircuitBreakerOpenError):
                await client.get("/api/v1/test")
            assert call_count == 4

            # Third request: breaker is open, no HTTP calls made
            with pytest.raises(CircuitBreakerOpenError):
                await client.get("/api/v1/test")
            assert call_count == 4
        finally:
            await client.close()
