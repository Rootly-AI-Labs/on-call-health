"""
Tests for token security and model properties.

Validates:
- Encryption parity between OAuth and manual tokens (both use Fernet)
- Round-trip encryption/decryption
- No plaintext tokens in encrypted output
- No plaintext tokens in error messages
- Token source discriminator and computed properties (is_oauth, is_manual, supports_refresh)
"""
import unittest
from unittest.mock import Mock, patch
import base64

from app.services.integration_validator import (
    encrypt_token,
    decrypt_token,
    get_encryption_key
)
from app.models import JiraIntegration, LinearIntegration


class TestTokenEncryptionParity(unittest.TestCase):
    """Verify OAuth and manual tokens receive identical encryption treatment."""

    def test_encrypt_uses_fernet(self):
        """Verify encrypt_token uses Fernet encryption."""
        token = "test_token_12345"
        encrypted = encrypt_token(token)

        # Fernet tokens start with 'gAAA' (base64 encoded timestamp prefix)
        self.assertTrue(encrypted.startswith('gAAA'))

    def test_encryption_key_is_consistent(self):
        """Verify same key used across calls (tokens use same protection)."""
        key1 = get_encryption_key()
        key2 = get_encryption_key()
        self.assertEqual(key1, key2)

    def test_same_token_different_ciphertext(self):
        """Verify Fernet produces unique ciphertexts (IV randomization prevents pattern analysis)."""
        token = "same_token_value"
        encrypted1 = encrypt_token(token)
        encrypted2 = encrypt_token(token)

        # Same plaintext should produce different ciphertext (Fernet uses random IV)
        self.assertNotEqual(encrypted1, encrypted2)

    def test_oauth_and_manual_token_encryption_identical(self):
        """Verify OAuth tokens and manual tokens use same encryption (equal protection)."""
        oauth_token = "oauth_access_token_xyz"
        manual_token = "manual_api_key_abc"

        oauth_encrypted = encrypt_token(oauth_token)
        manual_encrypted = encrypt_token(manual_token)

        # Both should decrypt correctly
        self.assertEqual(decrypt_token(oauth_encrypted), oauth_token)
        self.assertEqual(decrypt_token(manual_encrypted), manual_token)

        # Both should use same Fernet format (base64 encoded)
        self.assertTrue(oauth_encrypted.startswith('gAAA'))
        self.assertTrue(manual_encrypted.startswith('gAAA'))


class TestTokenDecryption(unittest.TestCase):
    """Verify token decryption works correctly - tokens recoverable with correct key."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that tokens can be encrypted and decrypted."""
        original = "my_secret_token_value"
        encrypted = encrypt_token(original)
        decrypted = decrypt_token(encrypted)
        self.assertEqual(original, decrypted)

    def test_decrypt_invalid_token_raises(self):
        """Test that invalid encrypted token raises exception (tampered data rejected)."""
        with self.assertRaises(Exception):
            decrypt_token("not_a_valid_encrypted_token")

    def test_decrypt_empty_string_raises(self):
        """Test that empty string raises exception."""
        with self.assertRaises(Exception):
            decrypt_token("")

    def test_special_characters_in_token(self):
        """Test tokens with special characters are handled correctly."""
        special_token = "token/with+special=chars&more"
        encrypted = encrypt_token(special_token)
        decrypted = decrypt_token(encrypted)
        self.assertEqual(special_token, decrypted)

    def test_unicode_in_token(self):
        """Test tokens with unicode characters are handled correctly."""
        unicode_token = "token_with_unicode_\u2603"
        encrypted = encrypt_token(unicode_token)
        decrypted = decrypt_token(encrypted)
        self.assertEqual(unicode_token, decrypted)


class TestNoPlaintextTokens(unittest.TestCase):
    """Verify plaintext tokens never appear in encrypted output."""

    def test_plaintext_not_in_encrypted(self):
        """Verify plaintext token not visible in encrypted form."""
        plaintext = "secret_token_12345"
        encrypted = encrypt_token(plaintext)

        # Encrypted should not contain plaintext substring
        self.assertNotIn(plaintext, encrypted)
        self.assertNotIn("secret", encrypted.lower())

    def test_encrypted_token_is_base64(self):
        """Verify encrypted token is valid base64."""
        token = "api_token_value"
        encrypted = encrypt_token(token)

        # Should be valid base64 (Fernet format)
        try:
            base64.urlsafe_b64decode(encrypted)
        except Exception:
            self.fail("Encrypted token is not valid base64")

    def test_model_token_fields_hold_encrypted_values(self):
        """Document that model access_token fields should hold encrypted values."""
        # This is a documentation test - models store encrypted tokens
        # Actual storage encryption is verified in integration tests
        jira = JiraIntegration()
        linear = LinearIntegration()

        # Both models have access_token field for encrypted storage
        self.assertTrue(hasattr(jira, 'access_token'))
        self.assertTrue(hasattr(linear, 'access_token'))

        # Both have token_source discriminator
        self.assertTrue(hasattr(jira, 'token_source'))
        self.assertTrue(hasattr(linear, 'token_source'))


class TestNoPlaintextInErrors(unittest.TestCase):
    """Verify error messages never contain plaintext tokens."""

    def test_decryption_error_no_token_leak(self):
        """Verify decryption errors don't leak the attempted token."""
        bad_token = "bad_encrypted_value_xyz123"

        with self.assertRaises(Exception) as context:
            decrypt_token(bad_token)

        # Error message should not contain the input
        error_msg = str(context.exception)
        self.assertNotIn(bad_token, error_msg)
        self.assertNotIn("xyz123", error_msg)


class TestTokenSourceDiscriminator(unittest.TestCase):
    """Verify token_source field and computed properties work correctly.

    This validates:
    - Success criterion #2: Database models distinguish OAuth vs manual via token_source
    - Success criterion #4: Integration models expose is_oauth, is_manual, supports_refresh
    """

    def test_jira_default_token_source_is_oauth(self):
        """Verify JiraIntegration defaults to oauth."""
        jira = JiraIntegration()
        # Column default applies at database level; verify column has correct default
        self.assertEqual(jira.__table__.columns['token_source'].default.arg, "oauth")

    def test_linear_default_token_source_is_oauth(self):
        """Verify LinearIntegration defaults to oauth."""
        linear = LinearIntegration()
        # Column default applies at database level; verify column has correct default
        self.assertEqual(linear.__table__.columns['token_source'].default.arg, "oauth")

    def test_jira_is_oauth_property(self):
        """Verify is_oauth property for Jira."""
        jira = JiraIntegration()
        jira.token_source = "oauth"
        self.assertTrue(jira.is_oauth)
        self.assertFalse(jira.is_manual)

    def test_jira_is_manual_property(self):
        """Verify is_manual property for Jira."""
        jira = JiraIntegration()
        jira.token_source = "manual"
        self.assertTrue(jira.is_manual)
        self.assertFalse(jira.is_oauth)

    def test_linear_is_oauth_property(self):
        """Verify is_oauth property for Linear."""
        linear = LinearIntegration()
        linear.token_source = "oauth"
        self.assertTrue(linear.is_oauth)
        self.assertFalse(linear.is_manual)

    def test_linear_is_manual_property(self):
        """Verify is_manual property for Linear."""
        linear = LinearIntegration()
        linear.token_source = "manual"
        self.assertTrue(linear.is_manual)
        self.assertFalse(linear.is_oauth)

    def test_jira_supports_refresh_oauth(self):
        """Verify supports_refresh for OAuth Jira with refresh token."""
        jira = JiraIntegration()
        jira.token_source = "oauth"
        jira.refresh_token = "encrypted_refresh_token"
        self.assertTrue(jira.supports_refresh)

    def test_jira_supports_refresh_manual(self):
        """Verify manual tokens don't support refresh."""
        jira = JiraIntegration()
        jira.token_source = "manual"
        jira.refresh_token = None
        self.assertFalse(jira.supports_refresh)

    def test_linear_supports_refresh_oauth(self):
        """Verify supports_refresh for OAuth Linear with refresh token."""
        linear = LinearIntegration()
        linear.token_source = "oauth"
        linear.refresh_token = "encrypted_refresh_token"
        self.assertTrue(linear.supports_refresh)

    def test_linear_supports_refresh_manual(self):
        """Verify manual tokens don't support refresh."""
        linear = LinearIntegration()
        linear.token_source = "manual"
        linear.refresh_token = None
        self.assertFalse(linear.supports_refresh)

    def test_jira_oauth_without_refresh_token(self):
        """Verify OAuth without refresh_token doesn't support refresh."""
        jira = JiraIntegration()
        jira.token_source = "oauth"
        jira.refresh_token = None
        self.assertFalse(jira.supports_refresh)

    def test_linear_oauth_without_refresh_token(self):
        """Verify OAuth without refresh_token doesn't support refresh."""
        linear = LinearIntegration()
        linear.token_source = "oauth"
        linear.refresh_token = None
        self.assertFalse(linear.supports_refresh)


if __name__ == '__main__':
    unittest.main()
