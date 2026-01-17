"""
HTTP utilities for reliable API calls with proper timeout and error handling.
"""
import aiohttp
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_default_timeout() -> aiohttp.ClientTimeout:
    """
    Get default timeout configuration for HTTP requests.

    Returns:
        ClientTimeout with sensible defaults:
        - total: 60s (maximum time for entire request)
        - connect: 10s (time to establish connection)
        - sock_read: 30s (time to read response data)

    This prevents:
    - Hanging connections during SSL handshake failures
    - ConnectionResetError exceptions from being unhandled
    - Indefinite waits on slow/broken API endpoints
    """
    return aiohttp.ClientTimeout(
        total=60,      # Total timeout for the entire request
        connect=10,    # Timeout for establishing connection (includes SSL handshake)
        sock_read=30   # Timeout for reading response data
    )


def create_session(timeout: Optional[aiohttp.ClientTimeout] = None) -> aiohttp.ClientSession:
    """
    Create an aiohttp ClientSession with proper timeout configuration.

    Args:
        timeout: Optional custom timeout. Uses get_default_timeout() if not provided.

    Returns:
        Configured ClientSession with timeouts

    Usage:
        async with create_session() as session:
            async with session.get(url) as resp:
                data = await resp.json()
    """
    if timeout is None:
        timeout = get_default_timeout()

    return aiohttp.ClientSession(
        timeout=timeout,
        connector=aiohttp.TCPConnector(
            limit=100,              # Limit total connections
            limit_per_host=30,      # Limit connections per host
            ttl_dns_cache=300,      # Cache DNS for 5 minutes
            ssl=True                # Enable SSL
        )
    )
