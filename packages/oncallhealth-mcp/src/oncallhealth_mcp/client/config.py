"""
Client configuration for the OnCallHealth REST API client.

Provides configuration dataclass with timeouts, connection pool limits,
and base URL settings for communicating with oncallhealth.ai APIs.
"""
import os
from dataclasses import dataclass, field

import httpx


@dataclass
class ClientConfig:
    """Configuration for the OnCallHealthClient.

    Attributes:
        base_url: oncallhealth.ai API base URL
        connect_timeout: Connection establishment timeout in seconds
        read_timeout: Response read timeout in seconds
        write_timeout: Request write timeout in seconds
        pool_timeout: Connection pool acquisition timeout in seconds
        max_connections: Maximum connections in the pool
        max_keepalive_connections: Maximum keepalive connections
        keepalive_expiry: Keepalive connection TTL in seconds
        max_client_age_seconds: Recreate client after this many seconds (default 4 hours)
        max_retries: Maximum retry attempts for transient failures
        retry_initial_wait: Initial wait time between retries in seconds
        retry_max_wait: Maximum wait time between retries in seconds
        retry_jitter: Random jitter added to retry delays (prevents thundering herd)
        circuit_breaker_fail_max: Consecutive failures to trip circuit breaker
        circuit_breaker_timeout_seconds: How long circuit breaker stays open
    """
    base_url: str = field(default_factory=lambda: os.environ.get(
        "ONCALLHEALTH_API_URL", "https://api.oncallhealth.ai"
    ))
    connect_timeout: float = 5.0
    read_timeout: float = 30.0
    write_timeout: float = 10.0
    pool_timeout: float = 5.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0
    max_client_age_seconds: int = 14400  # 4 hours
    # Retry settings
    max_retries: int = 3
    retry_initial_wait: float = 1.0
    retry_max_wait: float = 30.0
    retry_jitter: float = 1.0
    # Circuit breaker settings
    circuit_breaker_fail_max: int = 5
    circuit_breaker_timeout_seconds: int = 30

    @classmethod
    def from_env(cls) -> "ClientConfig":
        """Create ClientConfig from environment variables.

        Environment variables:
            ONCALLHEALTH_API_URL: Base URL for the API
            ONCALLHEALTH_CONNECT_TIMEOUT: Connection timeout (default: 5.0)
            ONCALLHEALTH_READ_TIMEOUT: Read timeout (default: 30.0)
            ONCALLHEALTH_WRITE_TIMEOUT: Write timeout (default: 10.0)
            ONCALLHEALTH_POOL_TIMEOUT: Pool timeout (default: 5.0)
            ONCALLHEALTH_MAX_CONNECTIONS: Max connections (default: 100)
            ONCALLHEALTH_MAX_KEEPALIVE: Max keepalive connections (default: 20)
            ONCALLHEALTH_KEEPALIVE_EXPIRY: Keepalive expiry seconds (default: 30.0)
            ONCALLHEALTH_MAX_CLIENT_AGE: Max client age seconds (default: 14400)
            ONCALLHEALTH_MAX_RETRIES: Max retry attempts (default: 3)
            ONCALLHEALTH_RETRY_INITIAL_WAIT: Initial retry wait seconds (default: 1.0)
            ONCALLHEALTH_RETRY_MAX_WAIT: Max retry wait seconds (default: 30.0)
            ONCALLHEALTH_RETRY_JITTER: Retry jitter seconds (default: 1.0)
            ONCALLHEALTH_CB_FAIL_MAX: Circuit breaker failure threshold (default: 5)
            ONCALLHEALTH_CB_TIMEOUT: Circuit breaker timeout seconds (default: 30)

        Returns:
            ClientConfig instance populated from environment
        """
        return cls(
            base_url=os.environ.get(
                "ONCALLHEALTH_API_URL", "https://api.oncallhealth.ai"
            ),
            connect_timeout=float(os.environ.get(
                "ONCALLHEALTH_CONNECT_TIMEOUT", "5.0"
            )),
            read_timeout=float(os.environ.get(
                "ONCALLHEALTH_READ_TIMEOUT", "30.0"
            )),
            write_timeout=float(os.environ.get(
                "ONCALLHEALTH_WRITE_TIMEOUT", "10.0"
            )),
            pool_timeout=float(os.environ.get(
                "ONCALLHEALTH_POOL_TIMEOUT", "5.0"
            )),
            max_connections=int(os.environ.get(
                "ONCALLHEALTH_MAX_CONNECTIONS", "100"
            )),
            max_keepalive_connections=int(os.environ.get(
                "ONCALLHEALTH_MAX_KEEPALIVE", "20"
            )),
            keepalive_expiry=float(os.environ.get(
                "ONCALLHEALTH_KEEPALIVE_EXPIRY", "30.0"
            )),
            max_client_age_seconds=int(os.environ.get(
                "ONCALLHEALTH_MAX_CLIENT_AGE", "14400"
            )),
            max_retries=int(os.environ.get(
                "ONCALLHEALTH_MAX_RETRIES", "3"
            )),
            retry_initial_wait=float(os.environ.get(
                "ONCALLHEALTH_RETRY_INITIAL_WAIT", "1.0"
            )),
            retry_max_wait=float(os.environ.get(
                "ONCALLHEALTH_RETRY_MAX_WAIT", "30.0"
            )),
            retry_jitter=float(os.environ.get(
                "ONCALLHEALTH_RETRY_JITTER", "1.0"
            )),
            circuit_breaker_fail_max=int(os.environ.get(
                "ONCALLHEALTH_CB_FAIL_MAX", "5"
            )),
            circuit_breaker_timeout_seconds=int(os.environ.get(
                "ONCALLHEALTH_CB_TIMEOUT", "30"
            )),
        )

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Create httpx.Timeout instance from this config.

        Returns:
            httpx.Timeout configured with connect, read, write, and pool timeouts
        """
        return httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=self.pool_timeout,
        )

    def to_httpx_limits(self) -> httpx.Limits:
        """Create httpx.Limits instance from this config.

        Returns:
            httpx.Limits configured with connection pool settings
        """
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry,
        )
