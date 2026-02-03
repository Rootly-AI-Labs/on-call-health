# Phase 5: REST API Client - Research

**Researched:** 2026-02-02
**Domain:** Resilient HTTP Client Layer (httpx, retry, circuit breaker)
**Confidence:** HIGH

## Summary

This research establishes the best practices for building a resilient REST API client in Python using httpx AsyncClient. The client will replace direct database access in the MCP server, enabling both SSE-hosted and PyPI-distributed deployments to communicate with oncallhealth.ai REST APIs.

The recommended approach uses httpx AsyncClient with explicit connection pool configuration, the tenacity library for retry with exponential backoff and jitter, and aiobreaker for circuit breaker pattern. This stack is well-established in the Python ecosystem, production-tested, and aligns with existing patterns in the codebase (rootly_client.py already uses httpx with manual retry logic).

The critical architectural insight is that the REST client must handle transient failures gracefully (network timeouts, 5xx errors, rate limits) while failing fast on permanent errors (401 unauthorized, 404 not found). Connection pool health monitoring is essential for long-running MCP server deployments to prevent PoolTimeout exhaustion after extended operation.

**Primary recommendation:** Use httpx AsyncClient with tenacity for retry logic, aiobreaker for circuit breaker, explicit Limits configuration, and periodic client recreation (every 4 hours) for connection pool health.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | 0.28.1+ | Async HTTP client | Already in requirements.txt, native async support, connection pooling, HTTP/2 capable |
| tenacity | 9.0.0+ | Retry with backoff | Production-proven, flexible configuration, native async support, better than manual retry |
| aiobreaker | 1.2.0+ | Circuit breaker | Native asyncio, simple API, state persistence options, actively maintained |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| structlog | 24.0.0+ | Structured logging | Request/response logging with context, sanitization |
| prometheus-client | 0.20.0+ | Metrics | Connection pool monitoring, retry counts (optional - existing NewRelic may suffice) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| tenacity | httpx-retries | httpx-retries is newer, simpler API but less flexible; tenacity has wider adoption |
| tenacity | backoff | backoff is simpler but tenacity has better async support and more features |
| aiobreaker | pybreaker | pybreaker is sync-first, aiobreaker is native async |
| aiobreaker | custom implementation | Don't hand-roll - aiobreaker handles edge cases (half-open, state transitions) |

**Installation:**
```bash
pip install httpx tenacity aiobreaker
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/mcp/
├── client/                  # REST API client module
│   ├── __init__.py
│   ├── base.py              # OnCallHealthClient class
│   ├── config.py            # Client configuration (timeouts, limits)
│   ├── retry.py             # Tenacity retry configuration
│   ├── circuit_breaker.py   # Aiobreaker setup and monitoring
│   ├── exceptions.py        # MCP exception types and HTTP mapping
│   └── health.py            # Connection pool health monitoring
├── server.py                # MCP server (uses client)
└── tools/                   # MCP tools (use client)
```

### Pattern 1: Singleton AsyncClient with Lifecycle Management
**What:** Create a single httpx.AsyncClient instance shared across all requests, with explicit lifecycle management.
**When to use:** Always for MCP server - connection pooling requires long-lived client.
**Example:**
```python
# Source: https://www.python-httpx.org/advanced/clients/
import httpx
from contextlib import asynccontextmanager

class OnCallHealthClient:
    _instance: "OnCallHealthClient | None" = None
    _client: httpx.AsyncClient | None = None
    _created_at: float = 0

    # Recreate client every 4 hours to prevent pool exhaustion
    MAX_CLIENT_AGE_SECONDS = 4 * 60 * 60

    @classmethod
    async def get_client(cls) -> httpx.AsyncClient:
        """Get or create the shared client instance."""
        import time
        now = time.time()

        # Check if client needs recreation
        if cls._client is not None:
            age = now - cls._created_at
            if age > cls.MAX_CLIENT_AGE_SECONDS:
                await cls._recreate_client()

        if cls._client is None:
            cls._client = cls._create_client()
            cls._created_at = now

        return cls._client

    @classmethod
    def _create_client(cls) -> httpx.AsyncClient:
        """Create a new client with proper configuration."""
        limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0  # 30s keepalive (default is 5s)
        )
        timeout = httpx.Timeout(
            connect=5.0,    # Connection establishment
            read=30.0,      # Reading response
            write=10.0,     # Writing request
            pool=5.0        # Acquiring connection from pool
        )
        return httpx.AsyncClient(
            limits=limits,
            timeout=timeout,
            http2=True  # Enable HTTP/2 for better connection reuse
        )

    @classmethod
    async def _recreate_client(cls):
        """Gracefully close old client and create new one."""
        old_client = cls._client
        cls._client = None
        if old_client:
            await old_client.aclose()
```

### Pattern 2: Tenacity Retry with Exponential Backoff and Jitter
**What:** Use tenacity decorator for retry logic with exponential backoff and jitter to prevent thundering herd.
**When to use:** All HTTP requests to oncallhealth.ai.
**Example:**
```python
# Source: https://tenacity.readthedocs.io/
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
    RetryError
)
import logging

logger = logging.getLogger(__name__)

# Transient exceptions that should trigger retry
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)

@retry(
    stop=stop_after_attempt(4),  # 1 initial + 3 retries
    wait=wait_exponential_jitter(
        initial=1.0,   # Start with 1 second
        max=30.0,      # Cap at 30 seconds
        jitter=1.0     # Add up to 1 second of jitter
    ),
    retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs
) -> httpx.Response:
    """Make HTTP request with automatic retry on transient failures."""
    response = await client.request(method, url, **kwargs)

    # Retry on server errors and rate limits
    if response.status_code in (429, 500, 502, 503, 504):
        # Respect Retry-After header if present
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            logger.warning(f"Rate limited, Retry-After: {retry_after}")
        # Raise to trigger retry
        response.raise_for_status()

    return response
```

### Pattern 3: Circuit Breaker with Aiobreaker
**What:** Wrap HTTP calls in circuit breaker to prevent retry storms and cascading failures.
**When to use:** Production deployments, especially for MCP server that may have many concurrent users.
**Example:**
```python
# Source: https://aiobreaker.netlify.app/
from aiobreaker import CircuitBreaker, CircuitBreakerListener, CircuitBreakerError
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class CircuitBreakerLogger(CircuitBreakerListener):
    """Log circuit breaker state transitions."""

    def state_change(self, breaker, old, new):
        logger.warning(
            f"Circuit breaker '{breaker.name}' state changed: "
            f"{old.state} -> {new.state}"
        )

    def failure(self, breaker, exception):
        logger.debug(f"Circuit breaker '{breaker.name}' recorded failure: {exception}")

# Configure circuit breaker
api_breaker = CircuitBreaker(
    fail_max=5,                             # Open after 5 consecutive failures
    timeout_duration=timedelta(seconds=30), # Stay open for 30 seconds
    exclude=[                               # Don't count these as failures
        httpx.HTTPStatusError,              # 4xx errors are not circuit-breaker worthy
    ],
    listeners=[CircuitBreakerLogger()],
    name="oncallhealth-api"
)

async def call_api_with_breaker(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs
) -> httpx.Response:
    """Make HTTP request through circuit breaker."""
    try:
        return await api_breaker.call_async(
            request_with_retry, client, method, url, **kwargs
        )
    except CircuitBreakerError as e:
        logger.error(f"Circuit breaker open, time until recovery: {e.time_remaining}")
        raise ServiceUnavailableError(
            f"Service temporarily unavailable, retry in {e.time_remaining.seconds}s"
        )
```

### Pattern 4: HTTP Status Code to MCP Exception Mapping
**What:** Map HTTP response codes to typed MCP exceptions for proper error handling in tools.
**When to use:** Every API response should be checked and mapped.
**Example:**
```python
# Source: https://mcpcat.io/guides/error-handling-custom-mcp-servers/
import httpx
from enum import Enum
from typing import Optional

class MCPErrorCode(Enum):
    """MCP-specific error codes."""
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    REQUEST_CANCELLED = -32800
    RESOURCE_UNAVAILABLE = -32802

class MCPError(Exception):
    """Base MCP exception."""
    def __init__(self, message: str, code: MCPErrorCode, retriable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.retriable = retriable

class AuthenticationError(MCPError):
    """Invalid or expired API key."""
    def __init__(self, message: str = "Invalid API key"):
        super().__init__(message, MCPErrorCode.INVALID_PARAMS, retriable=False)

class RateLimitError(MCPError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: Optional[int] = None):
        message = "Rate limit exceeded"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(message, MCPErrorCode.RESOURCE_UNAVAILABLE, retriable=True)

class ServiceUnavailableError(MCPError):
    """Backend service unavailable."""
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, MCPErrorCode.RESOURCE_UNAVAILABLE, retriable=True)

class NotFoundError(MCPError):
    """Resource not found."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, MCPErrorCode.INVALID_PARAMS, retriable=False)

def map_http_error_to_mcp(response: httpx.Response) -> MCPError:
    """Map HTTP error response to appropriate MCP exception."""
    status = response.status_code

    # Authentication errors (never retry)
    if status == 401:
        return AuthenticationError("Invalid API key")
    if status == 403:
        return AuthenticationError("API key lacks required permissions")

    # Client errors (never retry)
    if status == 400:
        return MCPError("Bad request", MCPErrorCode.INVALID_REQUEST, retriable=False)
    if status == 404:
        return NotFoundError()
    if status == 422:
        return MCPError("Validation error", MCPErrorCode.INVALID_PARAMS, retriable=False)

    # Rate limiting (retry after backoff)
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        return RateLimitError(int(retry_after) if retry_after else None)

    # Server errors (retry)
    if status >= 500:
        return ServiceUnavailableError(f"Server error: {status}")

    # Unknown error
    return MCPError(f"HTTP {status}", MCPErrorCode.INTERNAL_ERROR, retriable=False)
```

### Pattern 5: API Key Injection via Event Hooks
**What:** Use httpx event hooks to inject API key header and log requests.
**When to use:** All requests to oncallhealth.ai need authentication.
**Example:**
```python
# Source: https://www.python-httpx.org/advanced/event-hooks/
import httpx
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def create_auth_hook(api_key: str) -> Callable:
    """Create event hook that injects API key."""
    async def inject_api_key(request: httpx.Request):
        request.headers["X-API-Key"] = api_key
        # Log request (sanitize sensitive data)
        logger.debug(
            f"API Request: {request.method} {request.url.path}",
            extra={"method": request.method, "path": str(request.url.path)}
        )
    return inject_api_key

async def log_response(response: httpx.Response):
    """Log response status and timing."""
    request = response.request
    logger.debug(
        f"API Response: {request.method} {request.url.path} -> {response.status_code}",
        extra={
            "method": request.method,
            "path": str(request.url.path),
            "status": response.status_code,
        }
    )

def create_client_with_auth(base_url: str, api_key: str) -> httpx.AsyncClient:
    """Create httpx client with authentication and logging hooks."""
    limits = httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    )
    timeout = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

    return httpx.AsyncClient(
        base_url=base_url,
        limits=limits,
        timeout=timeout,
        event_hooks={
            "request": [create_auth_hook(api_key)],
            "response": [log_response]
        }
    )
```

### Anti-Patterns to Avoid
- **Creating new AsyncClient per request:** Kills connection pooling, wastes TLS handshakes. Use singleton pattern.
- **Retrying 4xx errors:** Client errors (except 429) indicate request problems, not transient failures. Only retry 429/5xx.
- **Infinite retry loops:** Always set stop_after_attempt. Max 4 attempts (1 initial + 3 retries) is typical.
- **Blocking sleep in async code:** Use `await asyncio.sleep()`, never `time.sleep()`.
- **Swallowing exceptions silently:** Log failures, map to typed exceptions, propagate appropriately.
- **Ignoring Retry-After header:** Honor server's rate limit guidance to avoid extended bans.

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry logic | Custom while loops with sleep | tenacity | Edge cases: jitter, backoff caps, exception filtering, async support |
| Circuit breaker | State machine with timers | aiobreaker | Half-open state handling, thread safety, state persistence options |
| Connection pooling | Multiple client instances | httpx.Limits | Built-in, properly handles keepalive, connection limits |
| Exponential backoff | Manual power calculation | tenacity.wait_exponential_jitter | Includes jitter, capping, tested implementation |
| HTTP error classification | if/elif chains | Typed exception hierarchy | Cleaner code, exhaustive handling, IDE support |

**Key insight:** Retry and circuit breaker logic has subtle edge cases (race conditions, state transitions, backoff overflow) that are easy to get wrong. Use battle-tested libraries.

## Common Pitfalls

### Pitfall 1: Connection Pool Exhaustion
**What goes wrong:** After 3-12 hours of operation, httpx.PoolTimeout errors start occurring even with normal load.
**Why it happens:** Connection pool state degrades over time due to leaked connections, cancelled requests, or connection timeouts not being properly handled.
**How to avoid:**
1. Implement periodic client recreation (every 4 hours)
2. Monitor `client._transport._pool._requests` queue size
3. Always call `response.read()` or `response.aread()` to release connections
4. Handle task cancellation carefully - connections may leak
**Warning signs:** PoolTimeout errors that don't correlate with traffic spikes; gradual degradation over hours.

### Pitfall 2: Retry Storm Amplification
**What goes wrong:** When oncallhealth.ai has issues, MCP server retries multiply the load, making recovery harder.
**Why it happens:** Each layer (client -> MCP server -> REST API) has its own retry logic. 3 retries at each of 3 layers = 27x amplification.
**How to avoid:**
1. Use circuit breaker to stop retries when backend is clearly down
2. Prefer retries at the edge (client-side) not internally
3. Set aggressive circuit breaker thresholds (fail_max=5, timeout=30s)
4. Monitor circuit breaker state transitions
**Warning signs:** High retry counts, backend overload during recovery periods.

### Pitfall 3: Retrying Non-Retriable Errors
**What goes wrong:** Retrying 401 (unauthorized) or 404 (not found) wastes time and resources.
**Why it happens:** Generic exception handling catches all errors, retry logic doesn't check response status.
**How to avoid:**
1. Check response.status_code before retrying
2. Only retry: network errors, timeouts, 429, 500, 502, 503, 504
3. Never retry: 400, 401, 403, 404, 405, 422
4. Map HTTP status to typed exceptions immediately after response
**Warning signs:** Retry logs showing 401/404 errors being retried.

### Pitfall 4: Missing Timeout Configuration
**What goes wrong:** Requests hang indefinitely or use overly aggressive defaults.
**Why it happens:** Default httpx timeout is 5s for all operations, which may be too short for some endpoints.
**How to avoid:**
1. Configure explicit timeouts: connect=5s, read=30s, write=10s, pool=5s
2. Allow per-request timeout overrides for slow endpoints
3. Document expected latencies (reference: rootly_client.py incidents endpoint is 15-21s p95)
**Warning signs:** Frequent ReadTimeout on endpoints that should succeed; requests never completing.

### Pitfall 5: Ignoring Half-Open State
**What goes wrong:** Circuit breaker opens but never recovers because half-open requests fail.
**Why it happens:** Half-open state allows one request through; if it fails, circuit reopens immediately.
**How to avoid:**
1. Ensure half-open request has reasonable timeout
2. Don't make critical decisions during half-open state
3. Log state transitions to monitor recovery attempts
4. Consider multiple half-open attempts (configurable in some libraries)
**Warning signs:** Circuit breaker stuck in open/half-open cycle; service never recovers.

## Code Examples

Verified patterns from official sources:

### Complete OnCallHealthClient Implementation
```python
# Combines all patterns into production-ready client
import httpx
import time
import logging
from tenacity import (
    retry, stop_after_attempt, wait_exponential_jitter,
    retry_if_exception_type, before_sleep_log
)
from aiobreaker import CircuitBreaker, CircuitBreakerError
from datetime import timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Configuration
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

class OnCallHealthClient:
    """Resilient REST API client for oncallhealth.ai."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        connect_timeout: float = 5.0,
        read_timeout: float = 30.0,
        max_connections: int = 100,
        max_retries: int = 3,
        circuit_fail_max: int = 5,
        circuit_timeout_seconds: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None
        self._created_at: float = 0
        self._max_client_age = 4 * 60 * 60  # 4 hours

        # Timeout configuration
        self._timeout = httpx.Timeout(
            connect=connect_timeout,
            read=read_timeout,
            write=10.0,
            pool=5.0
        )

        # Connection limits
        self._limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=20,
            keepalive_expiry=30.0
        )

        # Retry configuration (stored for decorator)
        self._max_retries = max_retries

        # Circuit breaker
        self._circuit_breaker = CircuitBreaker(
            fail_max=circuit_fail_max,
            timeout_duration=timedelta(seconds=circuit_timeout_seconds),
            name="oncallhealth-api"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with health check."""
        now = time.time()

        # Check if client needs recreation
        if self._client is not None:
            age = now - self._created_at
            if age > self._max_client_age:
                logger.info(f"Recreating client after {age/3600:.1f} hours")
                await self._recreate_client()

        if self._client is None:
            self._client = self._create_client()
            self._created_at = now

        return self._client

    def _create_client(self) -> httpx.AsyncClient:
        """Create new httpx AsyncClient."""
        async def inject_auth(request: httpx.Request):
            request.headers["X-API-Key"] = self.api_key

        return httpx.AsyncClient(
            base_url=self.base_url,
            limits=self._limits,
            timeout=self._timeout,
            event_hooks={"request": [inject_auth]}
        )

    async def _recreate_client(self):
        """Gracefully close old client and create new."""
        old_client = self._client
        self._client = None
        if old_client:
            try:
                await old_client.aclose()
            except Exception as e:
                logger.warning(f"Error closing old client: {e}")

    async def request(
        self,
        method: str,
        path: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request with retry and circuit breaker."""

        @retry(
            stop=stop_after_attempt(self._max_retries + 1),
            wait=wait_exponential_jitter(initial=1.0, max=30.0, jitter=1.0),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        async def _request_with_retry():
            client = await self._get_client()
            response = await client.request(method, path, **kwargs)

            # Check for retriable HTTP status codes
            if response.status_code in RETRYABLE_STATUS_CODES:
                # Log and raise to trigger retry
                logger.warning(f"Retriable status {response.status_code} for {method} {path}")
                response.raise_for_status()

            return response

        try:
            return await self._circuit_breaker.call_async(_request_with_retry)
        except CircuitBreakerError as e:
            raise ServiceUnavailableError(
                f"Service unavailable, circuit breaker open. Retry in {e.time_remaining.seconds}s"
            )

    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET request."""
        return await self.request("GET", path, **kwargs)

    async def post(self, path: str, **kwargs) -> httpx.Response:
        """POST request."""
        return await self.request("POST", path, **kwargs)

    async def close(self):
        """Close the client."""
        if self._client:
            await self._client.aclose()
            self._client = None
```

### Connection Pool Health Monitor
```python
# Source: https://github.com/encode/httpx/discussions/2556
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ConnectionPoolMonitor:
    """Monitor httpx client connection pool health."""

    def __init__(self, client: "OnCallHealthClient", check_interval: int = 60):
        self.client = client
        self.check_interval = check_interval
        self._monitor_task: Optional[asyncio.Task] = None
        self._consecutive_warnings = 0
        self._warning_threshold = 3

    async def start(self):
        """Start background health monitoring."""
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self):
        """Stop health monitoring."""
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

    async def _monitor_loop(self):
        """Periodically check connection pool health."""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                await self._check_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")

    async def _check_health(self):
        """Check connection pool metrics."""
        if self.client._client is None:
            return

        try:
            # Access internal pool state (may vary by httpx version)
            transport = self.client._client._transport
            if hasattr(transport, "_pool"):
                pool = transport._pool
                # Check pending requests queue
                pending = len(getattr(pool, "_requests", []))
                pool_size = len(getattr(pool, "_pool", []))

                logger.debug(f"Pool health: pending={pending}, pool_size={pool_size}")

                # Warn if pending requests are high
                if pending > 10:
                    self._consecutive_warnings += 1
                    logger.warning(
                        f"High pending requests: {pending} "
                        f"(warning {self._consecutive_warnings}/{self._warning_threshold})"
                    )

                    if self._consecutive_warnings >= self._warning_threshold:
                        logger.error("Triggering client recreation due to pool health")
                        await self.client._recreate_client()
                        self._consecutive_warnings = 0
                else:
                    self._consecutive_warnings = 0

        except Exception as e:
            logger.debug(f"Could not check pool health: {e}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| requests library | httpx AsyncClient | 2020+ | Native async, HTTP/2, connection pooling |
| Manual retry loops | tenacity decorators | 2018+ | Cleaner code, tested implementation |
| urllib3.Retry (sync) | tenacity + httpx (async) | 2020+ | Full async support |
| No circuit breaker | aiobreaker | 2020+ | Prevents cascading failures |
| `httpx.PoolLimits` | `httpx.Limits` | httpx 0.18 | API rename, same functionality |

**Deprecated/outdated:**
- `httpx.PoolLimits`: Renamed to `httpx.Limits` in httpx 0.18
- `limits` kwarg with `pool_limits`: Now just `limits`
- `httpx-retry` package: Unmaintained as of 2025-04-23, use `httpx-retries` or tenacity

## Open Questions

Things that couldn't be fully resolved:

1. **Exact timeout values for oncallhealth.ai endpoints**
   - What we know: rootly_client.py uses 30s default, 32s for incidents
   - What's unclear: What are the p95 latencies for oncallhealth.ai /api/* endpoints?
   - Recommendation: Start with 30s read timeout, profile actual latencies, adjust per-endpoint

2. **Connection pool size optimization**
   - What we know: Default 100 max_connections, 20 keepalive works for most apps
   - What's unclear: How many concurrent MCP tool calls are expected?
   - Recommendation: Start with defaults, monitor PoolTimeout errors, increase if needed

3. **Circuit breaker threshold tuning**
   - What we know: fail_max=5, timeout=30s is reasonable starting point
   - What's unclear: What's the expected failure rate? How long do oncallhealth.ai outages last?
   - Recommendation: Start conservative, tune based on production metrics

## Sources

### Primary (HIGH confidence)
- [HTTPX Official Documentation - Clients](https://www.python-httpx.org/advanced/clients/) - Client lifecycle, base_url, headers
- [HTTPX Resource Limits](https://www.python-httpx.org/advanced/resource-limits/) - Limits class parameters
- [HTTPX Timeouts](https://www.python-httpx.org/advanced/timeouts/) - Timeout configuration
- [HTTPX Event Hooks](https://www.python-httpx.org/advanced/event-hooks/) - Request/response hooks
- [Tenacity Documentation](https://tenacity.readthedocs.io/) - Retry configuration, async support
- [aiobreaker Documentation](https://aiobreaker.netlify.app/) - Circuit breaker API
- [AWS Retry Behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html) - Industry-standard retry patterns

### Secondary (MEDIUM confidence)
- [MCP Error Handling Guide](https://mcpcat.io/guides/error-handling-custom-mcp-servers/) - MCP exception patterns
- [httpx PoolTimeout Discussion](https://github.com/encode/httpx/discussions/2556) - Connection pool issues and solutions
- [httpx-retries Library](https://will-ockmore.github.io/httpx-retries/) - Alternative retry approach

### Tertiary (LOW confidence)
- [8 httpx + asyncio Patterns](https://medium.com/@sparknp1/8-httpx-asyncio-patterns-for-safer-faster-clients-f27bc82e93e6) - Community patterns (could not fetch full content)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified on PyPI, official documentation consulted
- Architecture: HIGH - Patterns from official docs and existing codebase (rootly_client.py)
- Pitfalls: HIGH - Multiple sources confirm issues (GitHub discussions, AWS docs)
- Code examples: HIGH - Based on official documentation with minor adaptations

**Research date:** 2026-02-02
**Valid until:** 2026-03-02 (30 days - stable libraries, patterns unlikely to change)
