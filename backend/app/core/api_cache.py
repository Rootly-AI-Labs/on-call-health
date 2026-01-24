"""
Generic API response caching using Redis.

Provides caching for external API responses (PagerDuty, Rootly, etc.)
with configurable TTLs and automatic fallback to in-memory cache.
"""
import hashlib
import json
import logging
import os
import random
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis

logger = logging.getLogger(__name__)

# In-memory fallback cache when Redis unavailable
_fallback_cache: Dict[str, Dict] = {}
_fallback_lock = threading.RLock()
_FALLBACK_MAX_SIZE = 100

# Sample rate for cache hit/miss logging (1 in N requests)
_LOG_SAMPLE_RATE = 10


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client for API caching (uses DB 0, same as oncall cache)."""
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return None
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable for API cache: {e}")
        return None


def _hash_token(token: str) -> str:
    """Create a secure hash of the API token for cache key isolation.

    Uses full SHA256 hash to avoid collisions.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def _build_cache_key(provider: str, endpoint: str, token: str, params: Optional[Dict] = None) -> str:
    """Build cache key including provider, endpoint, token hash, and optional params.

    Format: api:{provider}:{endpoint}:{token_hash}[:param_hash]
    """
    token_hash = _hash_token(token)
    base_key = f"api:{provider}:{endpoint}:{token_hash}"

    if params:
        # Include params in key for pagination/filter differentiation
        # Use SHA256 for consistency (truncated to 8 chars for readability)
        params_str = json.dumps(params, sort_keys=True)
        params_hash = hashlib.sha256(params_str.encode()).hexdigest()[:8]
        return f"{base_key}:{params_hash}"

    return base_key


def _should_log() -> bool:
    """Sample-rate logging to reduce noise."""
    return random.randint(1, _LOG_SAMPLE_RATE) == 1


def get_cached_api_response(
    provider: str,
    endpoint: str,
    token: str,
    params: Optional[Dict] = None
) -> Optional[Any]:
    """Get cached API response if available.

    Args:
        provider: API provider name (e.g., 'pagerduty', 'rootly')
        endpoint: API endpoint name (e.g., 'users', 'services')
        token: API token (used for cache key isolation)
        params: Optional query parameters (included in cache key)

    Returns:
        Cached data if available, None otherwise.
    """
    cache_key = _build_cache_key(provider, endpoint, token, params)

    # Try Redis first
    client = _get_redis_client()
    if client:
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                if _should_log():
                    logger.info(f"Cache HIT: {provider}:{endpoint}")
                return data.get("response")
            if _should_log():
                logger.debug(f"Cache MISS: {provider}:{endpoint}")
            return None
        except Exception as e:
            logger.warning(f"Redis read error for {provider}:{endpoint}: {e}")

    # Fallback to in-memory
    with _fallback_lock:
        if cache_key in _fallback_cache:
            entry = _fallback_cache[cache_key]
            if _should_log():
                logger.info(f"Cache HIT (fallback): {provider}:{endpoint}")
            return entry.get("response")

    return None


def set_cached_api_response(
    provider: str,
    endpoint: str,
    token: str,
    response: Any,
    ttl_seconds: int = 3600,
    params: Optional[Dict] = None
) -> bool:
    """Cache an API response.

    Args:
        provider: API provider name
        endpoint: API endpoint name
        token: API token
        response: The response data to cache
        ttl_seconds: Cache TTL in seconds (default: 1 hour)
        params: Optional query parameters

    Returns:
        True if cached successfully.
    """
    cache_key = _build_cache_key(provider, endpoint, token, params)

    data = {
        "response": response,
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "endpoint": endpoint
    }

    # Try Redis first
    client = _get_redis_client()
    if client:
        try:
            client.setex(cache_key, ttl_seconds, json.dumps(data))
            if _should_log():
                logger.info(f"Cached {provider}:{endpoint} (TTL: {ttl_seconds}s)")
            return True
        except Exception as e:
            logger.warning(f"Redis write error for {provider}:{endpoint}: {e}")

    # Fallback to in-memory with size limit
    with _fallback_lock:
        # Evict oldest entries if at capacity
        if len(_fallback_cache) >= _FALLBACK_MAX_SIZE and cache_key not in _fallback_cache:
            oldest_key = min(_fallback_cache.keys(), key=lambda k: _fallback_cache[k].get("cached_at", ""))
            del _fallback_cache[oldest_key]

        _fallback_cache[cache_key] = data
        if _should_log():
            logger.info(f"Cached {provider}:{endpoint} (fallback, TTL ignored)")
        return True


def invalidate_api_cache(
    provider: str,
    endpoint: str,
    token: str,
    params: Optional[Dict] = None
) -> bool:
    """Invalidate cached API response.

    Args:
        provider: API provider name
        endpoint: API endpoint name
        token: API token
        params: Optional query parameters

    Returns:
        True if invalidated successfully.
    """
    cache_key = _build_cache_key(provider, endpoint, token, params)

    # Try Redis
    client = _get_redis_client()
    if client:
        try:
            client.delete(cache_key)
            logger.info(f"Invalidated cache: {provider}:{endpoint}")
        except Exception as e:
            logger.warning(f"Redis delete error for {provider}:{endpoint}: {e}")

    # Also clear fallback
    with _fallback_lock:
        if cache_key in _fallback_cache:
            del _fallback_cache[cache_key]

    return True


def invalidate_provider_cache(provider: str, token: str) -> int:
    """Invalidate all cached responses for a provider/token combination.

    Useful when an integration is reconnected or credentials change.

    Returns:
        Number of keys invalidated.
    """
    token_hash = _hash_token(token)
    pattern = f"api:{provider}:*:{token_hash}*"
    count = 0

    client = _get_redis_client()
    if client:
        try:
            # Use SCAN instead of KEYS to avoid blocking Redis with large keyspaces
            keys_to_delete = []
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break
            if keys_to_delete:
                count = client.delete(*keys_to_delete)
                logger.info(f"Invalidated {count} cache entries for {provider}")
        except Exception as e:
            logger.warning(f"Redis pattern delete error for {provider}: {e}")

    # Also clear matching fallback entries
    # Key format: api:{provider}:{endpoint}:{token_hash}[:param_hash]
    # Check that token_hash is at the correct position (index 3 when split by :)
    with _fallback_lock:
        keys_to_delete = []
        for k in _fallback_cache.keys():
            if k.startswith(f"api:{provider}:"):
                parts = k.split(":")
                # parts[0]=api, parts[1]=provider, parts[2]=endpoint, parts[3]=token_hash
                if len(parts) >= 4 and parts[3] == token_hash:
                    keys_to_delete.append(k)
        for k in keys_to_delete:
            del _fallback_cache[k]
            count += 1

    return count
