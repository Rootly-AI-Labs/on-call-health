"""
Token refresh coordinator with distributed locking.

Coordinates OAuth token refresh operations across multiple application instances
using Redis-based distributed locks. Prevents concurrent refresh attempts and
provides token caching for waiting requests.
"""
import json
import logging
import os
from datetime import datetime, timezone as dt_timezone
from typing import Awaitable, Callable, Optional

import redis

from ..core.distributed_lock import with_distributed_lock

logger = logging.getLogger(__name__)

# Token cache TTL (1 minute) - short lived, just for concurrent request coordination
TOKEN_CACHE_TTL_SECONDS = 60


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client. Returns None if Redis is unavailable."""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable: {e}")
        return None


def _get_lock_config() -> tuple[int, float]:
    """
    Get lock configuration from environment variables.

    Returns:
        Tuple of (ttl_seconds, timeout_seconds)
    """
    ttl = int(os.getenv("TOKEN_REFRESH_LOCK_TTL", "30"))
    timeout = float(os.getenv("TOKEN_REFRESH_LOCK_TIMEOUT", "10"))
    return ttl, timeout


def _build_lock_key(provider: str, integration_id: int) -> str:
    """Build lock key for token refresh operation."""
    return f"token:refresh:{provider}:{integration_id}"


def _build_cache_key(provider: str, integration_id: int) -> str:
    """Build cache key for refreshed token."""
    return f"token:cache:{provider}:{integration_id}"


async def _get_cached_token(provider: str, integration_id: int) -> Optional[str]:
    """
    Get cached refreshed token if available.

    Args:
        provider: OAuth provider name (e.g., 'linear', 'github')
        integration_id: Integration ID

    Returns:
        Cached token if available and fresh, None otherwise
    """
    client = _get_redis_client()
    if not client:
        return None

    cache_key = _build_cache_key(provider, integration_id)

    try:
        cached_data = client.get(cache_key)
        if cached_data:
            data = json.loads(cached_data)
            logger.debug(f"Retrieved cached token for {provider} integration {integration_id}")
            return data.get("access_token")
    except Exception as e:
        logger.warning(f"Error retrieving cached token: {e}")

    return None


async def _cache_token(
    provider: str,
    integration_id: int,
    access_token: str,
    expires_at: Optional[datetime] = None
) -> None:
    """
    Cache refreshed token temporarily.

    Args:
        provider: OAuth provider name
        integration_id: Integration ID
        access_token: The access token to cache
        expires_at: Token expiry time (optional)
    """
    client = _get_redis_client()
    if not client:
        return

    cache_key = _build_cache_key(provider, integration_id)

    data = {
        "access_token": access_token,
        "cached_at": datetime.now(dt_timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None
    }

    try:
        client.setex(cache_key, TOKEN_CACHE_TTL_SECONDS, json.dumps(data))
        logger.debug(f"Cached token for {provider} integration {integration_id} (TTL: {TOKEN_CACHE_TTL_SECONDS}s)")
    except Exception as e:
        logger.warning(f"Error caching token: {e}")


async def refresh_token_with_lock(
    provider: str,
    integration_id: int,
    user_id: int,
    refresh_func: Callable[[], Awaitable[str]],
    fallback_func: Optional[Callable[[], Awaitable[str]]] = None
) -> str:
    """
    Coordinate token refresh with distributed locking.

    Attempts to acquire distributed lock before refreshing token. If lock is held
    by another process, waits for refresh to complete and retrieves cached token.
    Falls back to provided fallback function if Redis unavailable.

    Args:
        provider: OAuth provider name (e.g., 'linear', 'github')
        integration_id: Integration ID
        user_id: User ID (for logging)
        refresh_func: Async function that performs token refresh and returns new token
        fallback_func: Optional fallback function if Redis unavailable (e.g., DB locking)

    Returns:
        Valid access token

    Raises:
        RuntimeError: If token refresh fails or times out
    """
    lock_key = _build_lock_key(provider, integration_id)
    ttl_seconds, timeout_seconds = _get_lock_config()

    logger.info(
        f"[{provider.title()}] Token refresh coordination started: "
        f"user_id={user_id}, integration_id={integration_id}"
    )

    async with with_distributed_lock(lock_key, ttl_seconds, timeout_seconds) as lock_acquired:
        if not lock_acquired:
            # Redis unavailable or lock timeout
            logger.warning(
                f"[{provider.title()}] Distributed lock unavailable for user {user_id}, "
                f"integration {integration_id}"
            )

            # Check if another process cached the token while we waited
            cached_token = await _get_cached_token(provider, integration_id)
            if cached_token:
                logger.info(
                    f"[{provider.title()}] Using cached token for user {user_id} "
                    f"after lock timeout"
                )
                return cached_token

            # Fall back to alternative locking mechanism if provided
            if fallback_func:
                logger.info(
                    f"[{provider.title()}] Using fallback lock mechanism for user {user_id}"
                )
                return await fallback_func()

            raise RuntimeError(
                f"Failed to acquire lock for token refresh and no fallback available"
            )

        # Lock acquired - perform token refresh
        logger.info(
            f"[{provider.title()}] Acquired distributed lock, refreshing token: "
            f"user_id={user_id}, integration_id={integration_id}"
        )

        try:
            # Call the refresh function provided by caller
            new_token = await refresh_func()

            # Cache the new token for concurrent requests
            await _cache_token(provider, integration_id, new_token)

            logger.info(
                f"[{provider.title()}] Token refreshed successfully: "
                f"user_id={user_id}, integration_id={integration_id}"
            )

            return new_token

        except Exception as e:
            logger.error(
                f"[{provider.title()}] Token refresh failed: "
                f"user_id={user_id}, integration_id={integration_id}, error={e}"
            )
            raise


async def invalidate_token_cache(provider: str, integration_id: int) -> None:
    """
    Invalidate cached token.

    Call this when token is manually revoked or integration is disconnected.

    Args:
        provider: OAuth provider name
        integration_id: Integration ID
    """
    client = _get_redis_client()
    if not client:
        return

    cache_key = _build_cache_key(provider, integration_id)

    try:
        deleted = client.delete(cache_key)
        if deleted:
            logger.info(f"Invalidated token cache for {provider} integration {integration_id}")
    except Exception as e:
        logger.warning(f"Error invalidating token cache: {e}")
