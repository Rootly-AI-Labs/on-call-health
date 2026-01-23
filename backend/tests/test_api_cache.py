"""
Tests for API response caching module.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.core.api_cache import (
    get_cached_api_response,
    set_cached_api_response,
    invalidate_api_cache,
    invalidate_provider_cache,
    _build_cache_key,
    _hash_token,
    _fallback_cache,
    _fallback_lock,
    _FALLBACK_MAX_SIZE,
)


class TestApiCache(unittest.TestCase):
    """Test suite for API caching functions."""

    def setUp(self):
        """Clear fallback cache before each test."""
        with _fallback_lock:
            _fallback_cache.clear()

    def tearDown(self):
        """Clear fallback cache after each test."""
        with _fallback_lock:
            _fallback_cache.clear()

    def test_hash_token_produces_consistent_hash(self):
        """Test that token hashing is consistent."""
        token = "test_api_token_12345"
        hash1 = _hash_token(token)
        hash2 = _hash_token(token)
        self.assertEqual(hash1, hash2)
        # Full SHA256 should be 64 hex chars
        self.assertEqual(len(hash1), 64)

    def test_hash_token_different_tokens_different_hashes(self):
        """Test that different tokens produce different hashes."""
        hash1 = _hash_token("token1")
        hash2 = _hash_token("token2")
        self.assertNotEqual(hash1, hash2)

    def test_build_cache_key_basic(self):
        """Test basic cache key building."""
        key = _build_cache_key("pagerduty", "users", "test_token")
        self.assertTrue(key.startswith("api:pagerduty:users:"))
        # Should contain token hash
        self.assertIn(_hash_token("test_token"), key)

    def test_build_cache_key_with_params(self):
        """Test cache key building with params."""
        key1 = _build_cache_key("pagerduty", "users", "test_token", {"limit": 100})
        key2 = _build_cache_key("pagerduty", "users", "test_token", {"limit": 50})
        key3 = _build_cache_key("pagerduty", "users", "test_token", {"limit": 100})

        # Different params should produce different keys
        self.assertNotEqual(key1, key2)
        # Same params should produce same key
        self.assertEqual(key1, key3)

    @patch('app.core.api_cache._get_redis_client')
    def test_set_and_get_with_redis_unavailable(self, mock_redis):
        """Test that caching works with Redis unavailable (fallback)."""
        mock_redis.return_value = None

        data = [{"id": 1, "name": "User 1"}]
        set_cached_api_response("pagerduty", "users", "token123", data, ttl_seconds=3600)

        cached = get_cached_api_response("pagerduty", "users", "token123")
        self.assertEqual(cached, data)

    @patch('app.core.api_cache._get_redis_client')
    def test_get_nonexistent_key_returns_none(self, mock_redis):
        """Test that getting a non-existent key returns None."""
        mock_redis.return_value = None

        cached = get_cached_api_response("pagerduty", "users", "nonexistent_token")
        self.assertIsNone(cached)

    @patch('app.core.api_cache._get_redis_client')
    def test_invalidate_cache(self, mock_redis):
        """Test cache invalidation."""
        mock_redis.return_value = None

        data = [{"id": 1}]
        set_cached_api_response("pagerduty", "users", "token123", data)

        # Verify data is cached
        self.assertIsNotNone(get_cached_api_response("pagerduty", "users", "token123"))

        # Invalidate
        invalidate_api_cache("pagerduty", "users", "token123")

        # Verify data is gone
        self.assertIsNone(get_cached_api_response("pagerduty", "users", "token123"))

    @patch('app.core.api_cache._get_redis_client')
    def test_fallback_cache_size_limit(self, mock_redis):
        """Test that fallback cache respects size limit."""
        mock_redis.return_value = None

        # Fill cache to capacity
        for i in range(_FALLBACK_MAX_SIZE + 10):
            set_cached_api_response("pagerduty", "users", f"token_{i}", {"data": i})

        # Cache should not exceed max size
        with _fallback_lock:
            self.assertLessEqual(len(_fallback_cache), _FALLBACK_MAX_SIZE)

    @patch('app.core.api_cache._get_redis_client')
    def test_cache_with_params_isolation(self, mock_redis):
        """Test that same endpoint with different params are cached separately."""
        mock_redis.return_value = None

        data1 = [{"id": 1}]
        data2 = [{"id": 2}]

        set_cached_api_response("pagerduty", "users", "token", data1, params={"limit": 10})
        set_cached_api_response("pagerduty", "users", "token", data2, params={"limit": 20})

        cached1 = get_cached_api_response("pagerduty", "users", "token", params={"limit": 10})
        cached2 = get_cached_api_response("pagerduty", "users", "token", params={"limit": 20})

        self.assertEqual(cached1, data1)
        self.assertEqual(cached2, data2)

    @patch('app.core.api_cache._get_redis_client')
    def test_different_providers_different_cache(self, mock_redis):
        """Test that different providers have separate cache namespaces."""
        mock_redis.return_value = None

        pd_data = [{"provider": "pagerduty"}]
        rootly_data = [{"provider": "rootly"}]

        set_cached_api_response("pagerduty", "users", "token", pd_data)
        set_cached_api_response("rootly", "users", "token", rootly_data)

        cached_pd = get_cached_api_response("pagerduty", "users", "token")
        cached_rootly = get_cached_api_response("rootly", "users", "token")

        self.assertEqual(cached_pd, pd_data)
        self.assertEqual(cached_rootly, rootly_data)

    @patch('app.core.api_cache._get_redis_client')
    def test_redis_error_falls_back_gracefully(self, mock_redis):
        """Test that Redis errors fall back to in-memory gracefully."""
        # First call succeeds (for set), but get raises exception
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Redis connection error")
        mock_client.setex.side_effect = Exception("Redis connection error")
        mock_redis.return_value = mock_client

        # Should not raise, should fall back to in-memory
        data = [{"id": 1}]
        result = set_cached_api_response("pagerduty", "users", "token", data)
        self.assertTrue(result)  # Should succeed via fallback

        # Get should also fall back
        cached = get_cached_api_response("pagerduty", "users", "token")
        self.assertEqual(cached, data)


class TestInvalidateProviderCache(unittest.TestCase):
    """Test suite for provider-wide cache invalidation."""

    def setUp(self):
        with _fallback_lock:
            _fallback_cache.clear()

    def tearDown(self):
        with _fallback_lock:
            _fallback_cache.clear()

    @patch('app.core.api_cache._get_redis_client')
    def test_invalidate_provider_cache_clears_all_endpoints(self, mock_redis):
        """Test that invalidating provider cache clears all cached endpoints."""
        mock_redis.return_value = None

        token = "my_token"
        set_cached_api_response("pagerduty", "users", token, [{"id": 1}])
        set_cached_api_response("pagerduty", "services", token, [{"id": 2}])
        set_cached_api_response("rootly", "users", token, [{"id": 3}])

        # Invalidate all pagerduty cache for this token
        count = invalidate_provider_cache("pagerduty", token)

        # PagerDuty entries should be gone
        self.assertIsNone(get_cached_api_response("pagerduty", "users", token))
        self.assertIsNone(get_cached_api_response("pagerduty", "services", token))

        # Rootly entry should still exist
        self.assertIsNotNone(get_cached_api_response("rootly", "users", token))


if __name__ == '__main__':
    unittest.main()
