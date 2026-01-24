"""
Integration validation result caching using Redis.

Caches validation results (GitHub, Linear, Jira status) to avoid
redundant API calls when checking integration health.

TTL: 5 minutes (300 seconds) - same as previous in-memory cache.
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)

# Cache TTL in seconds (5 minutes)
VALIDATION_CACHE_TTL_SECONDS = 300

# In-memory fallback when Redis unavailable
_fallback_cache: Dict[int, Dict] = {}
_fallback_lock = threading.RLock()
_FALLBACK_MAX_SIZE = 1000


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for validation caching."""
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return None
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable for validation cache: {e}")
        return None


def _build_cache_key(user_id: int) -> str:
    """Build cache key for user validation results."""
    return f"validation:{user_id}"


def get_cached_validation(user_id: int) -> Optional[Dict[str, Dict[str, Any]]]:
    """Get cached validation results if still fresh.

    Args:
        user_id: The user ID to get cached results for.

    Returns:
        Cached validation results dict if available and fresh, None otherwise.
    """
    cache_key = _build_cache_key(user_id)

    # Try Redis first
    client = _get_redis_client()
    if client:
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                # Redis handles TTL, so if we get data it's still valid
                logger.info(f"Using cached validation results for user {user_id}")
                return data.get("results")
            return None
        except Exception as e:
            logger.warning(f"Redis read error for validation cache: {e}")

    # Fallback to in-memory
    with _fallback_lock:
        if user_id not in _fallback_cache:
            return None

        cached = _fallback_cache[user_id]
        cache_age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()

        if cache_age < VALIDATION_CACHE_TTL_SECONDS:
            logger.info(f"Using cached validation results for user {user_id} (fallback, age: {cache_age:.1f}s)")
            return cached["results"]

        # Cache expired, remove it
        del _fallback_cache[user_id]
        return None


def set_cached_validation(user_id: int, results: Dict[str, Dict[str, Any]]) -> bool:
    """Cache validation results.

    Args:
        user_id: The user ID to cache results for.
        results: The validation results dict.

    Returns:
        True if cached successfully.
    """
    cache_key = _build_cache_key(user_id)

    data = {
        "results": results,
        "cached_at": datetime.now(timezone.utc).isoformat()
    }

    # Try Redis first
    client = _get_redis_client()
    if client:
        try:
            client.setex(cache_key, VALIDATION_CACHE_TTL_SECONDS, json.dumps(data))
            logger.debug(f"Cached validation results for user {user_id} (TTL: {VALIDATION_CACHE_TTL_SECONDS}s)")
            return True
        except Exception as e:
            logger.warning(f"Redis write error for validation cache: {e}")

    # Fallback to in-memory with size limit
    with _fallback_lock:
        # Evict oldest entries if at capacity
        if len(_fallback_cache) >= _FALLBACK_MAX_SIZE and user_id not in _fallback_cache:
            # Defensive: use .get() in case entry is malformed
            oldest_user = min(
                _fallback_cache.keys(),
                key=lambda k: _fallback_cache[k].get("timestamp", datetime.min.replace(tzinfo=timezone.utc))
            )
            del _fallback_cache[oldest_user]
            logger.info(f"Evicted oldest validation cache entry for user {oldest_user}")

        _fallback_cache[user_id] = {
            "results": results,
            "timestamp": datetime.now(timezone.utc)
        }
        logger.debug(f"Cached validation results for user {user_id} (fallback)")
        return True


def invalidate_validation_cache(user_id: int) -> bool:
    """Invalidate cached validation results for a user.

    Call this when an integration is added, removed, or reconnected.

    Args:
        user_id: The user ID to invalidate cache for.

    Returns:
        True if invalidated successfully.
    """
    cache_key = _build_cache_key(user_id)

    # Try Redis
    client = _get_redis_client()
    if client:
        try:
            deleted = client.delete(cache_key)
            if deleted:
                logger.info(f"Invalidated validation cache for user {user_id}")
        except Exception as e:
            logger.warning(f"Redis delete error for validation cache: {e}")

    # Also clear fallback
    with _fallback_lock:
        if user_id in _fallback_cache:
            del _fallback_cache[user_id]
            logger.info(f"Invalidated validation cache for user {user_id} (fallback)")

    return True


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for monitoring.

    Returns:
        Dict with cache statistics.
    """
    stats = {
        "fallback_size": len(_fallback_cache),
        "fallback_max_size": _FALLBACK_MAX_SIZE,
        "ttl_seconds": VALIDATION_CACHE_TTL_SECONDS,
        "redis_available": False
    }

    client = _get_redis_client()
    if client:
        try:
            # Count validation keys using SCAN (non-blocking)
            key_count = 0
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match="validation:*", count=100)
                key_count += len(keys)
                if cursor == 0:
                    break
            stats["redis_available"] = True
            stats["redis_key_count"] = key_count
        except Exception:
            pass

    return stats
