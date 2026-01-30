"""
Unit tests for API Key model and service functions.

Tests cover:
- Key generation format (prefix, length, entropy)
- SHA-256 hashing (deterministic, correct length)
- Argon2id hashing (correct variant, verification)
- Model properties (is_active, masked_key, to_dict)
- Edge cases (expired keys, revoked keys)
"""

import pytest
from datetime import datetime, timedelta, timezone

# Service function imports
from app.services.api_key_service import (
    generate_api_key,
    verify_api_key,
    compute_sha256_hash,
)

# Model import
from app.models.api_key import APIKey


class TestKeyGeneration:
    """Tests for generate_api_key() function."""

    def test_returns_tuple_of_four_elements(self):
        """Test that generate_api_key returns a tuple with 4 elements."""
        result = generate_api_key()
        assert isinstance(result, tuple)
        assert len(result) == 4

    def test_full_key_has_correct_prefix(self):
        """Test that full key starts with 'och_live_' prefix."""
        full_key, _, _, _ = generate_api_key()
        assert full_key.startswith("och_live_")

    def test_full_key_has_correct_length(self):
        """Test that full key is exactly 73 characters (9 prefix + 64 hex)."""
        full_key, _, _, _ = generate_api_key()
        # 9 chars prefix "och_live_" + 64 hex chars = 73 total
        assert len(full_key) == 73

    def test_full_key_hex_part_is_valid_hex(self):
        """Test that the hex part of the key is valid hexadecimal."""
        full_key, _, _, _ = generate_api_key()
        hex_part = full_key[9:]  # Remove "och_live_" prefix
        # Should be valid hex - int() will raise ValueError if not
        int(hex_part, 16)
        assert len(hex_part) == 64

    def test_sha256_hash_has_correct_length(self):
        """Test that SHA-256 hash is exactly 64 hex characters."""
        _, sha256_hash, _, _ = generate_api_key()
        assert len(sha256_hash) == 64

    def test_sha256_hash_is_valid_hex(self):
        """Test that SHA-256 hash is valid hexadecimal."""
        _, sha256_hash, _, _ = generate_api_key()
        # Should be valid hex
        int(sha256_hash, 16)

    def test_argon2_hash_uses_argon2id_variant(self):
        """Test that Argon2 hash uses the argon2id variant."""
        _, _, argon2_hash, _ = generate_api_key()
        assert argon2_hash.startswith("$argon2id$")

    def test_last_four_has_correct_length(self):
        """Test that last_four is exactly 4 characters."""
        _, _, _, last_four = generate_api_key()
        assert len(last_four) == 4

    def test_last_four_matches_key_suffix(self):
        """Test that last_four matches the last 4 chars of the hex part."""
        full_key, _, _, last_four = generate_api_key()
        hex_part = full_key[9:]  # Remove prefix
        assert hex_part[-4:] == last_four

    def test_multiple_calls_produce_different_keys(self):
        """Test that multiple calls produce different keys (entropy)."""
        key1, _, _, _ = generate_api_key()
        key2, _, _, _ = generate_api_key()
        key3, _, _, _ = generate_api_key()
        # All three should be different
        assert key1 != key2
        assert key2 != key3
        assert key1 != key3

    def test_sha256_matches_computed_hash(self):
        """Test that returned SHA-256 matches compute_sha256_hash result."""
        full_key, sha256_hash, _, _ = generate_api_key()
        computed = compute_sha256_hash(full_key)
        assert computed == sha256_hash


class TestKeyVerification:
    """Tests for verify_api_key() function."""

    def test_correct_key_verifies_successfully(self):
        """Test that correct key verifies against its hash."""
        full_key, _, argon2_hash, _ = generate_api_key()
        result = verify_api_key(full_key, argon2_hash)
        assert result is True

    def test_wrong_key_fails_verification(self):
        """Test that wrong key fails verification."""
        _, _, argon2_hash, _ = generate_api_key()
        result = verify_api_key("wrong_key_that_doesnt_match", argon2_hash)
        assert result is False

    def test_empty_key_fails_verification(self):
        """Test that empty string fails verification."""
        _, _, argon2_hash, _ = generate_api_key()
        result = verify_api_key("", argon2_hash)
        assert result is False

    def test_wrong_hash_fails_verification(self):
        """Test that key fails against wrong hash."""
        full_key, _, _, _ = generate_api_key()
        # Create a different hash from a different key
        _, _, wrong_hash, _ = generate_api_key()
        result = verify_api_key(full_key, wrong_hash)
        assert result is False

    def test_malformed_hash_fails_gracefully(self):
        """Test that malformed hash fails gracefully without exception."""
        full_key, _, _, _ = generate_api_key()
        malformed_hash = "not_a_valid_argon2_hash"
        result = verify_api_key(full_key, malformed_hash)
        assert result is False

    def test_similar_key_fails_verification(self):
        """Test that a key with one character different fails."""
        full_key, _, argon2_hash, _ = generate_api_key()
        # Change one character
        modified_key = full_key[:-1] + ('0' if full_key[-1] != '0' else '1')
        result = verify_api_key(modified_key, argon2_hash)
        assert result is False


class TestSHA256Hash:
    """Tests for compute_sha256_hash() function."""

    def test_produces_64_characters(self):
        """Test that SHA-256 hash is exactly 64 characters."""
        result = compute_sha256_hash("test_key_value")
        assert len(result) == 64

    def test_produces_valid_hex(self):
        """Test that SHA-256 hash is valid hexadecimal."""
        result = compute_sha256_hash("test_key_value")
        int(result, 16)  # Should not raise

    def test_is_deterministic(self):
        """Test that same input always produces same hash."""
        hash1 = compute_sha256_hash("same_key")
        hash2 = compute_sha256_hash("same_key")
        hash3 = compute_sha256_hash("same_key")
        assert hash1 == hash2 == hash3

    def test_different_keys_produce_different_hashes(self):
        """Test that different inputs produce different hashes."""
        hash1 = compute_sha256_hash("key_one")
        hash2 = compute_sha256_hash("key_two")
        assert hash1 != hash2

    def test_empty_string_hashes(self):
        """Test that empty string produces a valid hash."""
        result = compute_sha256_hash("")
        assert len(result) == 64
        # Known SHA-256 of empty string
        assert result == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_hash_is_lowercase(self):
        """Test that hash is lowercase hexadecimal."""
        result = compute_sha256_hash("test")
        assert result == result.lower()


class TestAPIKeyModelIsActive:
    """Tests for APIKey.is_active property."""

    def test_is_active_when_not_revoked_not_expired(self):
        """Test is_active returns True when not revoked and no expiration."""
        api_key = APIKey(
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            revoked_at=None,
            expires_at=None
        )
        assert api_key.is_active is True

    def test_is_not_active_when_revoked(self):
        """Test is_active returns False when revoked_at is set."""
        api_key = APIKey(
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            revoked_at=datetime.now(timezone.utc),
            expires_at=None
        )
        assert api_key.is_active is False

    def test_is_not_active_when_expired(self):
        """Test is_active returns False when expires_at is in the past."""
        api_key = APIKey(
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            revoked_at=None,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        assert api_key.is_active is False

    def test_is_active_when_not_yet_expired(self):
        """Test is_active returns True when expires_at is in the future."""
        api_key = APIKey(
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            revoked_at=None,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        assert api_key.is_active is True

    def test_is_not_active_when_both_revoked_and_expired(self):
        """Test is_active returns False when both revoked and expired."""
        api_key = APIKey(
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            revoked_at=datetime.now(timezone.utc) - timedelta(days=7),
            expires_at=datetime.now(timezone.utc) - timedelta(days=1)
        )
        assert api_key.is_active is False


class TestAPIKeyModelMaskedKey:
    """Tests for APIKey.masked_key property."""

    def test_masked_key_format(self):
        """Test masked_key returns correct format."""
        api_key = APIKey(
            prefix="och_live_",
            last_four="xyz9",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$..."
        )
        assert api_key.masked_key == "och_live_...xyz9"

    def test_masked_key_with_different_values(self):
        """Test masked_key with different prefix and last_four values."""
        api_key = APIKey(
            prefix="test_",
            last_four="1234",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$..."
        )
        assert api_key.masked_key == "test_...1234"


class TestAPIKeyModelToDict:
    """Tests for APIKey.to_dict() method."""

    def test_to_dict_contains_expected_fields(self):
        """Test to_dict includes all expected fields."""
        now = datetime.now(timezone.utc)
        api_key = APIKey(
            id=1,
            name="Test Key",
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            scope="full_access",
            created_at=now,
            last_used_at=None,
            expires_at=None,
            revoked_at=None
        )
        result = api_key.to_dict()

        assert 'id' in result
        assert 'name' in result
        assert 'masked_key' in result
        assert 'scope' in result
        assert 'created_at' in result
        assert 'last_used_at' in result
        assert 'expires_at' in result
        assert 'is_active' in result
        assert 'revoked_at' in result

    def test_to_dict_does_not_contain_hashes(self):
        """Test to_dict does not expose sensitive hash fields."""
        api_key = APIKey(
            id=1,
            name="Test Key",
            key_hash_sha256="secret_sha256_hash_value",
            key_hash_argon2="$argon2id$secret_argon2_hash",
            prefix="och_live_",
            last_four="abcd"
        )
        result = api_key.to_dict()

        assert 'key_hash_sha256' not in result
        assert 'key_hash_argon2' not in result

    def test_to_dict_with_sensitive_true_includes_user_id(self):
        """Test to_dict with include_sensitive=True includes extra fields."""
        api_key = APIKey(
            id=1,
            user_id=42,
            name="Test Key",
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$..."
        )
        result = api_key.to_dict(include_sensitive=True)

        assert 'user_id' in result
        assert result['user_id'] == 42
        assert 'prefix' in result
        assert 'last_four' in result

    def test_to_dict_values_are_correct(self):
        """Test to_dict returns correct values."""
        now = datetime.now(timezone.utc)
        api_key = APIKey(
            id=123,
            name="My API Key",
            prefix="och_live_",
            last_four="wxyz",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            scope="full_access",
            created_at=now,
            last_used_at=None,
            expires_at=None,
            revoked_at=None
        )
        result = api_key.to_dict()

        assert result['id'] == 123
        assert result['name'] == "My API Key"
        assert result['masked_key'] == "och_live_...wxyz"
        assert result['scope'] == "full_access"
        assert result['is_active'] is True
        assert result['last_used_at'] is None
        assert result['expires_at'] is None

    def test_to_dict_formats_timestamps_as_iso(self):
        """Test to_dict formats datetime fields as ISO strings."""
        now = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
        api_key = APIKey(
            id=1,
            name="Test Key",
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            created_at=now,
            last_used_at=now,
            expires_at=now + timedelta(days=90),
            revoked_at=None
        )
        result = api_key.to_dict()

        assert result['created_at'] == "2024-06-15T10:30:00+00:00"
        assert result['last_used_at'] == "2024-06-15T10:30:00+00:00"
        assert result['expires_at'] == "2024-09-13T10:30:00+00:00"


class TestAPIKeyModelRepr:
    """Tests for APIKey.__repr__() method."""

    def test_repr_format(self):
        """Test __repr__ returns expected format."""
        api_key = APIKey(
            id=42,
            user_id=100,
            name="Production Key",
            prefix="och_live_",
            last_four="abcd",
            key_hash_sha256="a" * 64,
            key_hash_argon2="$argon2id$...",
            revoked_at=None,
            expires_at=None
        )
        repr_str = repr(api_key)

        assert "APIKey" in repr_str
        assert "id=42" in repr_str
        assert "name='Production Key'" in repr_str
        assert "user_id=100" in repr_str
        assert "is_active=True" in repr_str
