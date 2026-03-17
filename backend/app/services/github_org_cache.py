"""
Redis-backed cache for GitHub organization members and profiles.

Avoids re-fetching ~60 member profiles on every analysis/deploy,
saving GitHub API rate limit for actual activity data.
"""
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

import redis

logger = logging.getLogger(__name__)

# Org membership is stable — cache for 24 hours
ORG_MEMBERS_TTL_SECONDS = 86400
ORG_PROFILES_TTL_SECONDS = 86400

_fallback_cache: Dict[str, Dict] = {}
_fallback_lock = threading.RLock()


def _get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client."""
    try:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            return None
        client = redis.from_url(redis_url, decode_responses=True)
        client.ping()
        return client
    except Exception as e:
        logger.warning(f"Redis unavailable for github org cache: {e}")
        return None


def _build_cache_key(prefix: str, org: str) -> str:
    return f"github_org:{prefix}:{org}"


def get_cached_org_members(org: str) -> Optional[List[str]]:
    """Get cached org member logins."""
    cache_key = _build_cache_key("members", org)

    client = _get_redis_client()
    if client:
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Redis HIT: {len(data['members'])} members for {org}")
                return data["members"]
        except Exception as e:
            logger.warning(f"Redis read error for org members: {e}")

    with _fallback_lock:
        if cache_key in _fallback_cache:
            cached = _fallback_cache[cache_key]
            age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
            if age < ORG_MEMBERS_TTL_SECONDS:
                return cached["members"]
            del _fallback_cache[cache_key]

    return None


def set_cached_org_members(org: str, members: List[str]) -> None:
    """Cache org member logins."""
    cache_key = _build_cache_key("members", org)
    payload = {
        "members": members,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }

    client = _get_redis_client()
    if client:
        try:
            client.setex(cache_key, ORG_MEMBERS_TTL_SECONDS, json.dumps(payload))
            logger.info(f"Cached {len(members)} org members for {org} (TTL={ORG_MEMBERS_TTL_SECONDS}s)")
            return
        except Exception as e:
            logger.warning(f"Redis write error for org members: {e}")

    with _fallback_lock:
        _fallback_cache[cache_key] = {"members": members, "timestamp": datetime.now(timezone.utc)}


def get_cached_org_profiles(org: str) -> Optional[List[Dict]]:
    """Get cached org member profiles (login + display name)."""
    cache_key = _build_cache_key("profiles", org)

    client = _get_redis_client()
    if client:
        try:
            cached_data = client.get(cache_key)
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Redis HIT: {len(data['profiles'])} profiles for {org}")
                return data["profiles"]
        except Exception as e:
            logger.warning(f"Redis read error for org profiles: {e}")

    with _fallback_lock:
        if cache_key in _fallback_cache:
            cached = _fallback_cache[cache_key]
            age = (datetime.now(timezone.utc) - cached["timestamp"]).total_seconds()
            if age < ORG_PROFILES_TTL_SECONDS:
                return cached["profiles"]
            del _fallback_cache[cache_key]

    return None


def set_cached_org_profiles(org: str, profiles: List[Dict]) -> None:
    """Cache org member profiles."""
    cache_key = _build_cache_key("profiles", org)
    payload = {
        "profiles": profiles,
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }

    client = _get_redis_client()
    if client:
        try:
            client.setex(cache_key, ORG_PROFILES_TTL_SECONDS, json.dumps(payload))
            logger.info(f"Cached {len(profiles)} org profiles for {org} (TTL={ORG_PROFILES_TTL_SECONDS}s)")
            return
        except Exception as e:
            logger.warning(f"Redis write error for org profiles: {e}")

    with _fallback_lock:
        _fallback_cache[cache_key] = {"profiles": profiles, "timestamp": datetime.now(timezone.utc)}
