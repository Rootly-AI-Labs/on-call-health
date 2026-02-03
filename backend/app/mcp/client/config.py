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
