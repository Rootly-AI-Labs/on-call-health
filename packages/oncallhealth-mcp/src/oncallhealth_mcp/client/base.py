"""
OnCallHealth REST API client with connection pooling and API key injection.

Provides the core HTTP client that the MCP server uses to communicate with
oncallhealth.ai APIs, replacing direct database access.

Features:
- Connection pooling with configurable limits
- API key injection via event hooks
- Automatic retry with exponential backoff for transient failures
- Circuit breaker to prevent retry storms during outages
- Connection pool health monitoring with automatic recovery
"""
import logging
import time
from typing import Any, Optional, TYPE_CHECKING

import httpx
from aiobreaker import CircuitBreakerError

from .circuit_breaker import CircuitBreakerOpenError, create_circuit_breaker
from .config import ClientConfig
from .exceptions import map_http_error_to_mcp
from .retry import (
    RETRYABLE_STATUS_CODES,
    RetriableHTTPError,
    create_retry_decorator,
)

if TYPE_CHECKING:
    from .health import ConnectionPoolMonitor

logger = logging.getLogger(__name__)


class OnCallHealthClient:
    """Resilient REST API client for oncallhealth.ai.

    Features:
    - Connection pooling with configurable limits
    - API key injection via event hooks
    - Configurable timeouts (connect, read, write, pool)
    - Automatic client recreation after max age (default 4 hours)
    - HTTP error mapping to typed MCP exceptions
    - Automatic retry with exponential backoff for transient failures
    - Circuit breaker to prevent retry storms during outages
    - Connection pool health monitoring with automatic recovery

    Usage:
        async with OnCallHealthClient(api_key="...") as client:
            response = await client.get("/api/v1/users")

        # Or manual lifecycle management:
        client = OnCallHealthClient(api_key="...")
        try:
            response = await client.get("/api/v1/users")
        finally:
            await client.close()

        # With health monitoring:
        client = OnCallHealthClient(api_key="...")
        await client.start_health_monitor()
        try:
            response = await client.get("/api/v1/users")
        finally:
            await client.close()  # Automatically stops health monitor
    """

    def __init__(
        self,
        api_key: str,
        config: Optional[ClientConfig] = None,
    ):
        """Initialize the client.

        Args:
            api_key: API key for authentication (injected via X-API-Key header)
            config: Client configuration (uses defaults from environment if not provided)
        """
        self.api_key = api_key
        self.config = config or ClientConfig.from_env()
        self._client: Optional[httpx.AsyncClient] = None
        self._created_at: float = 0

        # Create circuit breaker with configured settings
        self._circuit_breaker = create_circuit_breaker(
            name="oncallhealth-api",
            fail_max=self.config.circuit_breaker_fail_max,
            timeout_seconds=self.config.circuit_breaker_timeout_seconds,
        )

        # Health monitor (started explicitly)
        self._health_monitor: Optional["ConnectionPoolMonitor"] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with health check.

        Returns:
            httpx.AsyncClient instance ready for use
        """
        now = time.time()

        # Check if client needs recreation due to age
        if self._client is not None:
            age = now - self._created_at
            if age > self.config.max_client_age_seconds:
                logger.info(
                    f"Recreating client after {age/3600:.1f} hours "
                    f"(max age: {self.config.max_client_age_seconds/3600:.1f} hours)"
                )
                await self._recreate_client()

        if self._client is None:
            self._client = self._create_client()
            self._created_at = now

        return self._client

    def _create_client(self) -> httpx.AsyncClient:
        """Create new httpx AsyncClient with configured settings.

        Returns:
            Configured httpx.AsyncClient instance
        """
        api_key = self.api_key

        async def inject_api_key(request: httpx.Request) -> None:
            """Event hook to inject API key header."""
            request.headers["X-API-Key"] = api_key

        async def log_response(response: httpx.Response) -> None:
            """Event hook to log response at DEBUG level."""
            request = response.request
            logger.debug(
                f"API Response: {request.method} {request.url.path} -> "
                f"{response.status_code}"
            )

        return httpx.AsyncClient(
            base_url=self.config.base_url,
            limits=self.config.to_httpx_limits(),
            timeout=self.config.to_httpx_timeout(),
            event_hooks={
                "request": [inject_api_key],
                "response": [log_response],
            },
        )

    async def _recreate_client(self) -> None:
        """Gracefully close old client and clear reference."""
        old_client = self._client
        self._client = None
        if old_client is not None:
            try:
                await old_client.aclose()
            except Exception as e:
                logger.warning(f"Error closing old client: {e}")

    async def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Make HTTP request with retry, circuit breaker, and error mapping.

        Requests are wrapped with:
        1. Circuit breaker - fails fast when service is down
        2. Retry with exponential backoff - handles transient failures
        3. Error mapping - converts HTTP errors to typed MCP exceptions

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            path: URL path (relative to base_url)
            **kwargs: Additional arguments passed to httpx.AsyncClient.request

        Returns:
            httpx.Response for successful requests (status < 400)

        Raises:
            CircuitBreakerOpenError: When circuit breaker is open
            MCPError: For HTTP errors (status >= 400), mapped to appropriate subclass
        """
        # Create retry decorator with configured settings
        retry_decorator = create_retry_decorator(
            max_retries=self.config.max_retries,
            initial_wait=self.config.retry_initial_wait,
            max_wait=self.config.retry_max_wait,
            jitter=self.config.retry_jitter,
        )

        @retry_decorator
        async def _request_with_retry() -> httpx.Response:
            """Inner function that handles retry logic."""
            client = await self._get_client()
            response = await client.request(method, path, **kwargs)

            # Check for retriable HTTP status codes
            if response.status_code in RETRYABLE_STATUS_CODES:
                logger.warning(
                    f"Retriable status {response.status_code} for {method} {path}"
                )
                raise RetriableHTTPError(response)

            # Map non-retriable errors to MCP exceptions (fail fast)
            if response.status_code >= 400:
                error = map_http_error_to_mcp(response)
                raise error

            return response

        try:
            # Wrap with circuit breaker
            return await self._circuit_breaker.call_async(_request_with_retry)
        except CircuitBreakerError as e:
            # Convert to our custom error with recovery time
            raise CircuitBreakerOpenError(
                self._circuit_breaker.name,
                e.time_remaining,
            )

    async def get(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make GET request.

        Args:
            path: URL path (relative to base_url)
            **kwargs: Additional arguments passed to request()

        Returns:
            httpx.Response for successful requests

        Raises:
            MCPError: For HTTP errors
        """
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make POST request.

        Args:
            path: URL path (relative to base_url)
            **kwargs: Additional arguments passed to request()

        Returns:
            httpx.Response for successful requests

        Raises:
            MCPError: For HTTP errors
        """
        return await self.request("POST", path, **kwargs)

    async def put(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make PUT request.

        Args:
            path: URL path (relative to base_url)
            **kwargs: Additional arguments passed to request()

        Returns:
            httpx.Response for successful requests

        Raises:
            MCPError: For HTTP errors
        """
        return await self.request("PUT", path, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> httpx.Response:
        """Make DELETE request.

        Args:
            path: URL path (relative to base_url)
            **kwargs: Additional arguments passed to request()

        Returns:
            httpx.Response for successful requests

        Raises:
            MCPError: For HTTP errors
        """
        return await self.request("DELETE", path, **kwargs)

    async def start_health_monitor(self, check_interval: int = 60) -> None:
        """Start connection pool health monitoring.

        Creates a background task that periodically checks pool health
        and triggers client recreation if degradation is detected.

        Args:
            check_interval: Seconds between health checks (default: 60)
        """
        if self._health_monitor is None:
            # Lazy import to avoid circular dependency
            from .health import ConnectionPoolMonitor

            self._health_monitor = ConnectionPoolMonitor(self, check_interval)
            await self._health_monitor.start()

    async def stop_health_monitor(self) -> None:
        """Stop health monitoring."""
        if self._health_monitor is not None:
            await self._health_monitor.stop()
            self._health_monitor = None

    async def close(self) -> None:
        """Close the HTTP client and release resources.

        Also stops the health monitor if running.
        """
        await self.stop_health_monitor()
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "OnCallHealthClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit - ensures client is closed."""
        await self.close()
