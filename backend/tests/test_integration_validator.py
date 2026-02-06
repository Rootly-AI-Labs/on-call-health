"""
Tests for integration validation service.
"""
import unittest
from datetime import datetime, timedelta, timezone as dt_timezone
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
import httpx
import asyncio

from app.services.integration_validator import (
    IntegrationValidator,
    needs_refresh,
    _is_ascii_digits,
    _parse_expires_in,
    EXPIRES_IN_DEFAULT_SECONDS,
    EXPIRES_IN_MIN_SECONDS,
    EXPIRES_IN_MAX_SECONDS,
)
from app.core.validation_cache import (
    get_cached_validation,
    set_cached_validation,
    invalidate_validation_cache,
    VALIDATION_CACHE_TTL_SECONDS,
    _fallback_cache,
    _fallback_lock,
    _FALLBACK_MAX_SIZE,
)
from app.models import GitHubIntegration, LinearIntegration, JiraIntegration


class TestIntegrationValidator(unittest.TestCase):
    """Test suite for IntegrationValidator service."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    # GitHub Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_success(self, mock_decrypt):
        """Test successful GitHub validation."""
        # Setup
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.user_id = 1
        mock_integration.github_token = "encrypted_token"

        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        # Mock httpx response
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            # Execute
            result = self._run_async(self.validator._validate_github(user_id=1))

        # Assert
        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_expired_token(self, mock_decrypt):
        """Test GitHub validation with expired token (401)."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "expired_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_forbidden(self, mock_decrypt):
        """Test GitHub validation with forbidden token (403)."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "forbidden_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 403
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("lacks required permissions", result["error"])

    def test_validate_github_no_integration(self):
        """Test GitHub validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertIsNone(result)

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_timeout(self, mock_decrypt):
        """Test GitHub validation with timeout."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("timed out", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_network_error(self, mock_decrypt):
        """Test GitHub validation with network error."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                side_effect=httpx.NetworkError("Network error")
            )

            result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("Cannot reach", result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_github_decryption_error(self, mock_decrypt):
        """Test GitHub validation with decryption error."""
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.side_effect = Exception("Decryption failed")

        result = self._run_async(self.validator._validate_github(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("decryption failed", result["error"].lower())

    # Linear Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_linear_success(self, mock_decrypt):
        """Test successful Linear validation."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        mock_integration.refresh_token = None
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"viewer": {"id": "123"}}}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_linear_graphql_error(self, mock_decrypt):
        """Test Linear validation with GraphQL unauthorized error."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        mock_integration.refresh_token = None
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "invalid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"errors": [{"message": "Unauthorized"}]}
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    def test_validate_linear_no_integration(self):
        """Test Linear validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_linear(user_id=1))

        self.assertIsNone(result)

    # Jira Validation Tests

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_jira_success(self, mock_decrypt):
        """Test successful Jira validation."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.jira_cloud_id = "test-cloud-id"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "valid_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertTrue(result["valid"])
        self.assertIsNone(result["error"])

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_jira_expired_token(self, mock_decrypt):
        """Test Jira validation with expired token (401)."""
        mock_integration = Mock(spec=JiraIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.jira_cloud_id = "test-cloud-id"
        self.mock_db.query().filter().first.return_value = mock_integration
        mock_decrypt.return_value = "expired_token"

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)

            result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertFalse(result["valid"])
        self.assertIn("expired or invalid", result["error"])

    def test_validate_jira_no_integration(self):
        """Test Jira validation when no integration exists."""
        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator._validate_jira(user_id=1))

        self.assertIsNone(result)


class TestValidationCache(unittest.TestCase):
    """Test suite for validation caching functions."""

    def setUp(self):
        """Clear cache before each test."""
        _fallback_cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        _fallback_cache.clear()

    def test_set_and_get_cached_validation(self):
        """Test setting and retrieving cached validation results."""
        user_id = 1
        results = {
            "github": {"valid": True, "error": None},
            "linear": {"valid": False, "error": "Token expired"}
        }

        set_cached_validation(user_id, results)
        cached = get_cached_validation(user_id)

        self.assertEqual(cached, results)

    def test_get_cached_validation_not_exists(self):
        """Test getting cache for non-existent user returns None."""
        cached = get_cached_validation(999)
        self.assertIsNone(cached)

    def test_get_cached_validation_expired(self):
        """Test that expired cache returns None."""
        user_id = 1
        results = {"github": {"valid": True, "error": None}}

        # Set cache with old timestamp
        _fallback_cache[user_id] = {
            "results": results,
            "timestamp": datetime.now(dt_timezone.utc) - timedelta(seconds=VALIDATION_CACHE_TTL_SECONDS + 10)
        }

        cached = get_cached_validation(user_id)
        self.assertIsNone(cached)

    def test_invalidate_validation_cache(self):
        """Test invalidating cache for a user."""
        user_id = 1
        results = {"github": {"valid": True, "error": None}}

        set_cached_validation(user_id, results)
        self.assertIsNotNone(get_cached_validation(user_id))

        invalidate_validation_cache(user_id)
        self.assertIsNone(get_cached_validation(user_id))

    def test_invalidate_validation_cache_nonexistent_user(self):
        """Test invalidating cache for non-existent user does not raise."""
        invalidate_validation_cache(999)

    def test_cache_expired_entry_removed(self):
        """Test that expired cache entry is removed on access."""
        user_id = 1
        results = {"github": {"valid": True, "error": None}}

        # Set cache with old timestamp directly
        with _fallback_lock:
            _fallback_cache[user_id] = {
                "results": results,
                "timestamp": datetime.now(dt_timezone.utc) - timedelta(seconds=VALIDATION_CACHE_TTL_SECONDS + 10)
            }

        # Access should return None and remove the entry
        cached = get_cached_validation(user_id)
        self.assertIsNone(cached)

        # Entry should be removed
        with _fallback_lock:
            self.assertNotIn(user_id, _fallback_cache)

    def test_cache_eviction_when_full(self):
        """Test that oldest entries are evicted when cache is full."""
        # Fill the cache to _FALLBACK_MAX_SIZE
        base_time = datetime.now(dt_timezone.utc) - timedelta(hours=1)

        with _fallback_lock:
            for i in range(_FALLBACK_MAX_SIZE):
                _fallback_cache[i] = {
                    "results": {"github": {"valid": True, "error": None}},
                    "timestamp": base_time + timedelta(seconds=i)
                }

        # Adding a new entry should trigger eviction
        set_cached_validation(_FALLBACK_MAX_SIZE + 1, {"github": {"valid": True, "error": None}})

        # Cache should now be smaller than _FALLBACK_MAX_SIZE + 1
        with _fallback_lock:
            self.assertLess(len(_fallback_cache), _FALLBACK_MAX_SIZE + 1)
            # New entry should exist
            self.assertIn(_FALLBACK_MAX_SIZE + 1, _fallback_cache)


class TestNeedsRefresh(unittest.TestCase):
    """Test suite for needs_refresh function."""

    def test_needs_refresh_no_expiry(self):
        """Test that None expiry returns False."""
        self.assertFalse(needs_refresh(None))

    def test_needs_refresh_expired(self):
        """Test that expired token returns True."""
        expired = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        self.assertTrue(needs_refresh(expired))

    def test_needs_refresh_within_buffer(self):
        """Test that token expiring within buffer returns True."""
        expiring_soon = datetime.now(dt_timezone.utc) + timedelta(minutes=30)
        self.assertTrue(needs_refresh(expiring_soon, skew_minutes=60))

    def test_needs_refresh_not_needed(self):
        """Test that token with plenty of time returns False."""
        far_future = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        self.assertFalse(needs_refresh(far_future))


class TestLinearTokenRefresh(unittest.TestCase):
    """Test suite for Linear token refresh functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)
        # Setup transaction context manager mock
        self._setup_transaction_mock()

    def _setup_transaction_mock(self):
        """Configure mock db to handle transaction context managers."""
        self.mock_db.in_transaction.return_value = False
        mock_transaction = Mock()
        mock_transaction.__enter__ = Mock(return_value=None)
        mock_transaction.__exit__ = Mock(return_value=False)
        self.mock_db.begin.return_value = mock_transaction
        self.mock_db.begin_nested.return_value = mock_transaction

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_no_refresh_needed(self, mock_decrypt):
        """Test getting token when no refresh is needed."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "valid_token"

        token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertEqual(token, "valid_token")
        mock_decrypt.assert_called_once_with("encrypted_token")

    @patch('app.services.integration_validator.encrypt_token')
    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_refresh_success(self, mock_decrypt, mock_encrypt):
        """Test successful token refresh with row locking."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.id = 1
        mock_integration.user_id = 1
        mock_integration.access_token = "old_encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "refresh_token_value"
        mock_encrypt.return_value = "new_encrypted_token"

        # Mock the FOR UPDATE query chain - returns same integration (still needs refresh)
        mock_query = Mock()
        mock_filter = Mock()
        mock_with_for_update = Mock()
        mock_with_for_update.first.return_value = mock_integration
        mock_filter.with_for_update.return_value = mock_with_for_update
        mock_query.filter.return_value = mock_filter
        self.mock_db.query.return_value = mock_query

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
                "expires_in": 86400
            }
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertEqual(token, "new_access_token")
        # Transaction commit is handled by context manager __exit__
        self.mock_db.begin.return_value.__exit__.assert_called()

    def test_get_valid_linear_token_no_refresh_token_raises_error(self):
        """Test that expired token with no refresh token raises an error."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) - timedelta(minutes=10)
        mock_integration.refresh_token = None

        with self.assertRaises(ValueError) as context:
            self._run_async(self.validator._get_valid_linear_token(mock_integration))

        # Generic error message to avoid information disclosure
        self.assertIn("Authentication error", str(context.exception))

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_refresh_fails(self, mock_decrypt):
        """Test that refresh failure always raises exception."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.id = 1
        mock_integration.user_id = 1
        mock_integration.access_token = "old_encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(minutes=30)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "refresh_token_value"

        # Mock the FOR UPDATE query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_with_for_update = Mock()
        mock_with_for_update.first.return_value = mock_integration
        mock_filter.with_for_update.return_value = mock_with_for_update
        mock_query.filter.return_value = mock_filter
        self.mock_db.query.return_value = mock_query

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            with self.assertRaises(ValueError) as context:
                self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertIn("authentication error", str(context.exception).lower())
        self.mock_db.rollback.assert_called()

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_already_refreshed_by_another_request(self, mock_decrypt):
        """Test that double-check pattern works - skip refresh if already done."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.id = 1
        mock_integration.user_id = 1
        mock_integration.access_token = "old_encrypted_token"
        # Token needs refresh based on initial check
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(minutes=30)
        mock_integration.refresh_token = "encrypted_refresh"

        # But after acquiring lock, another request already refreshed it
        locked_integration = Mock(spec=LinearIntegration)
        locked_integration.access_token = "already_refreshed_token"
        # Token is now fresh (far future expiry)
        locked_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)

        mock_decrypt.return_value = "already_refreshed_decrypted"

        # Mock the FOR UPDATE query chain
        mock_query = Mock()
        mock_filter = Mock()
        mock_with_for_update = Mock()
        mock_with_for_update.first.return_value = locked_integration
        mock_filter.with_for_update.return_value = mock_with_for_update
        mock_query.filter.return_value = mock_filter
        self.mock_db.query.return_value = mock_query

        # Should return the already-refreshed token without calling Linear API
        with patch('httpx.AsyncClient') as mock_client:
            token = self._run_async(self.validator._get_valid_linear_token(mock_integration))

            # HTTP client should NOT have been called since token was already refreshed
            mock_client.return_value.__aenter__.return_value.post.assert_not_called()

        self.assertEqual(token, "already_refreshed_decrypted")

    def test_get_valid_linear_token_no_access_token(self):
        """Test that missing access_token raises ValueError."""
        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.access_token = None
        mock_integration.token_expires_at = None
        mock_integration.refresh_token = None

        with self.assertRaises(ValueError) as context:
            self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertIn("No access token available", str(context.exception))

    @patch('app.services.integration_validator.decrypt_token')
    def test_get_valid_linear_token_database_lock_error(self, mock_decrypt):
        """Test that database lock errors are handled as transient/retryable."""
        from sqlalchemy.exc import OperationalError

        mock_integration = Mock(spec=LinearIntegration)
        mock_integration.id = 1
        mock_integration.user_id = 1
        mock_integration.access_token = "encrypted_token"
        mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(minutes=30)
        mock_integration.refresh_token = "encrypted_refresh"
        mock_decrypt.return_value = "token_value"

        # Mock the query to raise OperationalError (database lock timeout)
        mock_query = Mock()
        mock_filter = Mock()
        mock_filter.with_for_update.side_effect = OperationalError("statement", {}, "lock timeout")
        mock_query.filter.return_value = mock_filter
        self.mock_db.query.return_value = mock_query

        # Raises RuntimeError (retryable) instead of ValueError (permanent)
        with self.assertRaises(RuntimeError) as context:
            self._run_async(self.validator._get_valid_linear_token(mock_integration))

        self.assertIn("Temporary error", str(context.exception))
        self.mock_db.rollback.assert_called_once()

    def test_safe_rollback_success(self):
        """Test _safe_rollback handles successful rollback."""
        self.validator._safe_rollback()
        self.mock_db.rollback.assert_called_once()

    def test_safe_rollback_handles_failure(self):
        """Test _safe_rollback handles rollback failure gracefully."""
        self.mock_db.rollback.side_effect = Exception("Rollback failed")

        # Should not raise - just logs the error
        self.validator._safe_rollback()
        self.mock_db.rollback.assert_called_once()



class TestIsAsciiDigits(unittest.TestCase):
    """Test suite for _is_ascii_digits helper function."""

    def test_valid_ascii_digits(self):
        """Test that valid ASCII digit strings return True."""
        self.assertTrue(_is_ascii_digits("123"))
        self.assertTrue(_is_ascii_digits("0"))
        self.assertTrue(_is_ascii_digits("9876543210"))

    def test_empty_string_returns_false(self):
        """Test that empty string returns False."""
        self.assertFalse(_is_ascii_digits(""))

    def test_non_digit_characters_return_false(self):
        """Test that strings with non-digit characters return False."""
        self.assertFalse(_is_ascii_digits("12a3"))
        self.assertFalse(_is_ascii_digits("-123"))
        self.assertFalse(_is_ascii_digits("1.5"))
        self.assertFalse(_is_ascii_digits("1e9"))

    def test_unicode_digits_return_false(self):
        """Test that Unicode digits (like superscript) return False."""
        self.assertFalse(_is_ascii_digits("³"))
        self.assertFalse(_is_ascii_digits("²³"))
        self.assertFalse(_is_ascii_digits("12³"))


class TestParseExpiresIn(unittest.TestCase):
    """Test suite for _parse_expires_in function."""

    def test_none_returns_default(self):
        """Test that None returns the default value."""
        self.assertEqual(_parse_expires_in(None), EXPIRES_IN_DEFAULT_SECONDS)

    def test_bool_returns_default(self):
        """Test that boolean values return the default."""
        self.assertEqual(_parse_expires_in(True), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in(False), EXPIRES_IN_DEFAULT_SECONDS)

    def test_valid_int_within_bounds(self):
        """Test that valid integers within bounds are returned."""
        self.assertEqual(_parse_expires_in(3600), 3600)
        self.assertEqual(_parse_expires_in(EXPIRES_IN_MIN_SECONDS), EXPIRES_IN_MIN_SECONDS)
        self.assertEqual(_parse_expires_in(EXPIRES_IN_MAX_SECONDS), EXPIRES_IN_MAX_SECONDS)

    def test_int_below_min_returns_default(self):
        """Test that integers below minimum return default."""
        self.assertEqual(_parse_expires_in(1), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in(0), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in(-100), EXPIRES_IN_DEFAULT_SECONDS)

    def test_int_above_max_returns_default(self):
        """Test that integers above maximum return default."""
        self.assertEqual(_parse_expires_in(EXPIRES_IN_MAX_SECONDS + 1), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in(10**10), EXPIRES_IN_DEFAULT_SECONDS)

    def test_valid_string_within_bounds(self):
        """Test that valid string numbers within bounds are returned."""
        self.assertEqual(_parse_expires_in("3600"), 3600)
        self.assertEqual(_parse_expires_in(" 3600 "), 3600)

    def test_invalid_string_returns_default(self):
        """Test that invalid string formats return default."""
        self.assertEqual(_parse_expires_in("abc"), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in("1e9"), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in("-100"), EXPIRES_IN_DEFAULT_SECONDS)
        self.assertEqual(_parse_expires_in("1.5"), EXPIRES_IN_DEFAULT_SECONDS)

    def test_float_within_bounds(self):
        """Test that floats within valid range are accepted."""
        self.assertEqual(_parse_expires_in(3600.0), 3600)
        # 1e3 = 1000.0, within bounds
        self.assertEqual(_parse_expires_in(1e3), 1000)

    def test_scientific_notation_float_rejected_early(self):
        """Test that large scientific notation floats are rejected BEFORE int conversion.

        This prevents potential integer overflow issues. The bounds check happens
        on the raw float value, not after conversion to int.
        """
        # 1e9 = 1,000,000,000 which exceeds EXPIRES_IN_MAX_SECONDS (2,592,000)
        self.assertEqual(_parse_expires_in(1e9), EXPIRES_IN_DEFAULT_SECONDS)
        # Very large float that could cause overflow if converted first
        self.assertEqual(_parse_expires_in(1e15), EXPIRES_IN_DEFAULT_SECONDS)
        # Negative large float
        self.assertEqual(_parse_expires_in(-1e9), EXPIRES_IN_DEFAULT_SECONDS)

    def test_non_integer_float_returns_default(self):
        """Test that non-integer floats return default."""
        self.assertEqual(_parse_expires_in(3600.5), EXPIRES_IN_DEFAULT_SECONDS)



class TestValidateAllIntegrations(unittest.TestCase):
    """Test suite for validate_all_integrations with caching."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=Session)
        self.validator = IntegrationValidator(self.mock_db)
        _fallback_cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        _fallback_cache.clear()

    def _run_async(self, coro):
        """Helper to run async functions in tests."""
        return asyncio.run(coro)

    def test_validate_all_uses_cache(self):
        """Test that validate_all_integrations uses cached results."""
        user_id = 1
        cached_results = {
            "github": {"valid": True, "error": None}
        }
        set_cached_validation(user_id, cached_results)

        result = self._run_async(self.validator.validate_all_integrations(user_id, use_cache=True))

        self.assertEqual(result, cached_results)

    def test_validate_all_returns_cached_jira_result(self):
        """Test that cached jira result is returned by validate_all_integrations.

        This is the pattern used by the Jira /status endpoint to avoid
        calling _validate_jira() directly and bypassing the cache.
        """
        user_id = 1
        cached_results = {
            "github": {"valid": True, "error": None},
            "jira": {"valid": True, "error": None},
        }
        set_cached_validation(user_id, cached_results)

        result = self._run_async(self.validator.validate_all_integrations(user_id, use_cache=True))

        self.assertEqual(result.get("jira"), {"valid": True, "error": None})

    def test_validate_all_returns_none_for_missing_jira(self):
        """Test that .get('jira') returns None when jira is not in cached results."""
        user_id = 1
        cached_results = {
            "github": {"valid": True, "error": None},
        }
        set_cached_validation(user_id, cached_results)

        result = self._run_async(self.validator.validate_all_integrations(user_id, use_cache=True))

        self.assertIsNone(result.get("jira"))

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_all_bypasses_cache(self, mock_decrypt):
        """Test that validate_all_integrations bypasses cache when use_cache=False."""
        user_id = 1
        cached_results = {"github": {"valid": True, "error": None}}
        set_cached_validation(user_id, cached_results)

        self.mock_db.query().filter().first.return_value = None

        result = self._run_async(self.validator.validate_all_integrations(user_id, use_cache=False))

        self.assertEqual(result, {})

    @patch('app.services.integration_validator.decrypt_token')
    def test_validate_all_caches_results(self, mock_decrypt):
        """Test that validate_all_integrations caches fresh results."""
        user_id = 1
        mock_integration = Mock(spec=GitHubIntegration)
        mock_integration.github_token = "encrypted_token"
        mock_decrypt.return_value = "valid_token"

        def query_side_effect():
            mock_query = Mock()
            mock_filter = Mock()
            mock_filter.first.return_value = mock_integration
            mock_query.filter.return_value = mock_filter
            return mock_query

        self.mock_db.query.side_effect = query_side_effect

        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"viewer": {"id": "123"}}}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

            self._run_async(self.validator.validate_all_integrations(user_id, use_cache=False))

        cached = get_cached_validation(user_id)
        self.assertIsNotNone(cached)


if __name__ == '__main__':
    unittest.main()
