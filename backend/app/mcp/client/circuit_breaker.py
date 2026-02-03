"""
Circuit breaker configuration for OnCallHealth REST API client.

Uses aiobreaker to prevent retry storms when the backend is consistently
failing. The circuit breaker opens after consecutive failures and provides
automatic recovery via half-open state.
"""
import logging
from datetime import timedelta

from aiobreaker import CircuitBreaker, CircuitBreakerListener

import httpx

logger = logging.getLogger(__name__)


class CircuitBreakerLogger(CircuitBreakerListener):
    """Log circuit breaker state transitions.

    Provides visibility into circuit breaker behavior for monitoring
    and debugging purposes.
    """

    def state_change(self, breaker: CircuitBreaker, old, new) -> None:
        """Log when circuit breaker changes state.

        Args:
            breaker: The circuit breaker instance
            old: Previous state
            new: New state
        """
        logger.warning(
            f"Circuit breaker '{breaker.name}' state: {old.state} -> {new.state}"
        )

    def failure(self, breaker: CircuitBreaker, exception: Exception) -> None:
        """Log circuit breaker failures.

        Args:
            breaker: The circuit breaker instance
            exception: The exception that caused the failure
        """
        logger.debug(f"Circuit breaker '{breaker.name}' failure: {exception}")

    def success(self, breaker: CircuitBreaker) -> None:
        """Log circuit breaker successes.

        Args:
            breaker: The circuit breaker instance
        """
        logger.debug(f"Circuit breaker '{breaker.name}' success")


class CircuitBreakerOpenError(Exception):
    """Circuit breaker is open, service unavailable.

    Raised when attempts are made to call a protected function while
    the circuit breaker is in the open state.

    Attributes:
        name: Name of the circuit breaker that is open
        time_remaining: Estimated time until the circuit breaker
            transitions to half-open state
    """

    def __init__(self, name: str, time_remaining: timedelta):
        self.name = name
        self.time_remaining = time_remaining
        seconds = int(time_remaining.total_seconds())
        super().__init__(
            f"Circuit breaker '{name}' is open. Retry in {seconds}s"
        )


def create_circuit_breaker(
    name: str = "oncallhealth-api",
    fail_max: int = 5,
    timeout_seconds: int = 30,
) -> CircuitBreaker:
    """Create configured circuit breaker.

    The circuit breaker monitors failures and automatically opens when
    fail_max consecutive failures occur. When open, it rejects all calls
    immediately without attempting the operation. After timeout_seconds,
    it transitions to half-open state and allows one test request through.

    4xx HTTP errors (client errors) are excluded from failure counting
    since they indicate client issues, not server problems.

    Args:
        name: Identifier for the circuit breaker (for logging)
        fail_max: Number of consecutive failures before circuit opens
        timeout_seconds: Duration in seconds the circuit stays open

    Returns:
        Configured CircuitBreaker instance

    Example:
        breaker = create_circuit_breaker(fail_max=5, timeout_seconds=30)

        try:
            result = await breaker.call_async(make_request)
        except CircuitBreakerError:
            # Circuit is open, handle gracefully
            pass
    """
    return CircuitBreaker(
        fail_max=fail_max,
        timeout_duration=timedelta(seconds=timeout_seconds),
        exclude=[httpx.HTTPStatusError],  # 4xx errors don't trip breaker
        listeners=[CircuitBreakerLogger()],
        name=name,
    )
