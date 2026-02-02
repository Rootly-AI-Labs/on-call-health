"""
Unit tests for MCP API key authentication.

Tests cover:
- X-API-Key header extraction from various context shapes
- JWT rejection in MCP context
- Expired/revoked key handling
- Valid key authentication
"""
import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from app.mcp.auth import (
    extract_api_key_header,
    require_user_api_key,
)


class TestExtractApiKeyHeader:
    """Tests for X-API-Key header extraction."""

    def test_extract_from_request_headers(self):
        """Should extract X-API-Key from request_headers."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123"})
        assert extract_api_key_header(ctx) == "och_live_test123"

    def test_extract_from_headers_lowercase(self):
        """Should handle lowercase header name."""
        ctx = SimpleNamespace(headers={"x-api-key": "och_live_test456"})
        assert extract_api_key_header(ctx) == "och_live_test456"

    def test_extract_from_headers_uppercase(self):
        """Should handle uppercase header name."""
        ctx = SimpleNamespace(headers={"X-API-KEY": "och_live_test789"})
        assert extract_api_key_header(ctx) == "och_live_test789"

    def test_extract_from_request_object(self):
        """Should extract from request.headers."""
        class DummyRequest:
            headers = {"X-API-Key": "och_live_test789"}

        ctx = SimpleNamespace(request=DummyRequest())
        assert extract_api_key_header(ctx) == "och_live_test789"

    def test_extract_missing_returns_none(self):
        """Should return None when header not present."""
        ctx = SimpleNamespace()
        assert extract_api_key_header(ctx) is None

    def test_extract_empty_headers(self):
        """Should return None for empty headers."""
        ctx = SimpleNamespace(headers={})
        assert extract_api_key_header(ctx) is None

    def test_extract_with_whitespace(self):
        """Should strip whitespace from header value."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "  och_live_test123  "})
        result = extract_api_key_header(ctx)
        assert result == "och_live_test123"

    def test_extract_empty_value_returns_none(self):
        """Should return None for empty header value."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": ""})
        assert extract_api_key_header(ctx) is None

    def test_extract_priority_request_headers_first(self):
        """Should prioritize request_headers over headers."""
        ctx = SimpleNamespace(
            request_headers={"X-API-Key": "och_live_from_request_headers"},
            headers={"X-API-Key": "och_live_from_headers"}
        )
        assert extract_api_key_header(ctx) == "och_live_from_request_headers"


class TestRequireUserApiKeyJwtRejection:
    """Tests for JWT rejection in MCP context."""

    def test_jwt_rejected_with_permission_error(self):
        """JWT token should be rejected with PermissionError."""
        ctx = SimpleNamespace(
            request_headers={"Authorization": "Bearer jwt_token_here"},
            headers={}
        )
        db = Mock()

        with pytest.raises(PermissionError) as exc_info:
            require_user_api_key(ctx, db)

        assert "API key authentication" in str(exc_info.value)
        assert "Bearer token" in str(exc_info.value)

    def test_jwt_with_x_api_key_prefers_rejection(self):
        """JWT with X-API-Key header should still reject JWT."""
        ctx = SimpleNamespace(
            request_headers={
                "Authorization": "Bearer jwt_token_here",
                "X-API-Key": "och_live_test123"
            }
        )
        db = Mock()

        with pytest.raises(PermissionError) as exc_info:
            require_user_api_key(ctx, db)

        assert "API key authentication" in str(exc_info.value)


class TestRequireUserApiKeyMissing:
    """Tests for missing API key handling."""

    def test_missing_key_raises_permission_error(self):
        """Missing API key should raise PermissionError."""
        ctx = SimpleNamespace()
        db = Mock()

        with pytest.raises(PermissionError) as exc_info:
            require_user_api_key(ctx, db)

        assert "Missing API key" in str(exc_info.value)

    def test_empty_key_raises_permission_error(self):
        """Empty API key should raise PermissionError."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": ""})
        db = Mock()

        with pytest.raises(PermissionError) as exc_info:
            require_user_api_key(ctx, db)

        assert "Missing API key" in str(exc_info.value)


class TestRequireUserApiKeyInvalidFormat:
    """Tests for invalid key format."""

    def test_wrong_prefix_rejected(self):
        """Key without och_live_ prefix should be rejected."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "sk_live_wrong"})
        db = Mock()

        with pytest.raises(PermissionError) as exc_info:
            require_user_api_key(ctx, db)

        assert "och_live_" in str(exc_info.value)

    def test_partial_prefix_rejected(self):
        """Key with partial prefix should be rejected."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_test123"})
        db = Mock()

        with pytest.raises(PermissionError) as exc_info:
            require_user_api_key(ctx, db)

        assert "och_live_" in str(exc_info.value)


class TestRequireUserApiKeyNotFound:
    """Tests for key not found in database."""

    def test_unknown_key_raises_permission_error(self):
        """Unknown key should raise PermissionError."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_unknown123456789"})

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(PermissionError) as exc_info:
                require_user_api_key(ctx, db)

        assert "Invalid API key" in str(exc_info.value)


class TestRequireUserApiKeyRevoked:
    """Tests for revoked key handling."""

    def test_revoked_key_raises_permission_error(self):
        """Revoked key should raise PermissionError."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = datetime.now(timezone.utc)
        mock_api_key.expires_at = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(PermissionError) as exc_info:
                require_user_api_key(ctx, db)

        assert "revoked" in str(exc_info.value).lower()


class TestRequireUserApiKeyExpired:
    """Tests for expired key handling."""

    def test_expired_key_includes_date(self):
        """Expired key error should include expiration date."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        # Use a past date to ensure key is expired
        expiry_date = datetime(2025, 12, 15, tzinfo=timezone.utc)
        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = expiry_date

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(PermissionError) as exc_info:
                require_user_api_key(ctx, db)

        assert "2025-12-15" in str(exc_info.value)

    def test_expired_key_message_contains_expired(self):
        """Expired key error should contain 'expired'."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        expiry_date = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = expiry_date

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with pytest.raises(PermissionError) as exc_info:
                require_user_api_key(ctx, db)

        assert "expired" in str(exc_info.value).lower()


class TestRequireUserApiKeyArgon2Failure:
    """Tests for Argon2 verification failure."""

    def test_argon2_failure_raises_permission_error(self):
        """Argon2 verification failure should raise PermissionError."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        db = Mock()
        db.query.return_value = mock_query

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.mcp.auth.verify_api_key', return_value=False):
                with pytest.raises(PermissionError) as exc_info:
                    require_user_api_key(ctx, db)

        assert "Invalid API key" in str(exc_info.value)


class TestRequireUserApiKeyUserNotFound:
    """Tests for orphaned API key (user deleted)."""

    def test_orphaned_key_raises_permission_error(self):
        """API key with deleted user should raise PermissionError."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 999

        # Mock database - APIKey found, User not found
        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = None
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.mcp.auth.verify_api_key', return_value=True):
                with pytest.raises(PermissionError) as exc_info:
                    require_user_api_key(ctx, db)

        assert "owner not found" in str(exc_info.value).lower()


class TestRequireUserApiKeyValid:
    """Tests for valid API key authentication."""

    def test_valid_key_returns_user(self):
        """Valid API key should return user."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = None
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 42

        mock_user = Mock()
        mock_user.id = 42

        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.mcp.auth.verify_api_key', return_value=True):
                user = require_user_api_key(ctx, db)

        assert user == mock_user
        assert user.id == 42

    def test_valid_key_with_future_expiry_returns_user(self):
        """Valid API key with future expiry should return user."""
        ctx = SimpleNamespace(request_headers={"X-API-Key": "och_live_test123456789"})

        # Key expires 30 days from now
        from datetime import timedelta
        future_expiry = datetime.now(timezone.utc) + timedelta(days=30)

        mock_api_key = Mock()
        mock_api_key.id = 1
        mock_api_key.revoked_at = None
        mock_api_key.expires_at = future_expiry
        mock_api_key.key_hash_argon2 = "test_hash"
        mock_api_key.user_id = 42

        mock_user = Mock()
        mock_user.id = 42

        def mock_query_side_effect(model):
            mock_query = Mock()
            if model.__name__ == 'APIKey':
                mock_query.filter.return_value.first.return_value = mock_api_key
            elif model.__name__ == 'User':
                mock_query.filter.return_value.first.return_value = mock_user
            return mock_query

        db = Mock()
        db.query.side_effect = mock_query_side_effect

        with patch('app.mcp.auth.compute_sha256_hash', return_value="test_sha256"):
            with patch('app.mcp.auth.verify_api_key', return_value=True):
                user = require_user_api_key(ctx, db)

        assert user == mock_user
