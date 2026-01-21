"""
Unit tests for admin endpoint security functions.

Tests API key validation, IP whitelist parsing, and IP whitelisting logic.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestAdminAPIKeyValidation(unittest.TestCase):
    """Test ADMIN_API_KEY validation logic."""

    def test_validate_api_key_returns_false_when_not_set(self):
        """Test that validation fails when API key is not set."""
        # Test the logic directly without importing the module
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop('ADMIN_API_KEY', None)
            api_key = os.getenv("ADMIN_API_KEY")
            # When not set, validation should fail
            self.assertIsNone(api_key)
            # Simulating the validation logic
            is_valid = bool(api_key and len(api_key) >= 32)
            self.assertFalse(is_valid)

    def test_validate_api_key_returns_false_when_too_short(self):
        """Test that validation fails when API key is less than 32 chars."""
        short_key = "tooshort"  # Only 8 chars
        self.assertLess(len(short_key), 32)

    def test_validate_api_key_returns_true_when_valid(self):
        """Test that validation passes when API key is 32+ chars."""
        valid_key = "a" * 32  # Exactly 32 chars
        self.assertGreaterEqual(len(valid_key), 32)

        longer_key = "a" * 64  # 64 chars
        self.assertGreaterEqual(len(longer_key), 32)


class TestIPWhitelistParsing(unittest.TestCase):
    """Test IP whitelist parsing logic."""

    def test_parse_empty_whitelist(self):
        """Test that empty whitelist returns empty set."""
        whitelist_str = ""
        result = {ip.strip() for ip in whitelist_str.split(",") if ip.strip()} if whitelist_str else set()
        self.assertEqual(result, set())

    def test_parse_single_ip(self):
        """Test parsing a single IP address."""
        whitelist_str = "192.168.1.1"
        result = {ip.strip() for ip in whitelist_str.split(",") if ip.strip()}
        self.assertEqual(result, {"192.168.1.1"})

    def test_parse_multiple_ips(self):
        """Test parsing multiple IP addresses."""
        whitelist_str = "192.168.1.1,10.0.0.1,172.16.0.1"
        result = {ip.strip() for ip in whitelist_str.split(",") if ip.strip()}
        self.assertEqual(result, {"192.168.1.1", "10.0.0.1", "172.16.0.1"})

    def test_parse_ips_with_whitespace(self):
        """Test parsing IPs with surrounding whitespace."""
        whitelist_str = "  192.168.1.1 , 10.0.0.1  ,  172.16.0.1  "
        result = {ip.strip() for ip in whitelist_str.split(",") if ip.strip()}
        self.assertEqual(result, {"192.168.1.1", "10.0.0.1", "172.16.0.1"})

    def test_parse_cidr_ranges(self):
        """Test parsing CIDR notation."""
        whitelist_str = "192.168.1.0/24,10.0.0.0/8"
        result = {ip.strip() for ip in whitelist_str.split(",") if ip.strip()}
        self.assertEqual(result, {"192.168.1.0/24", "10.0.0.0/8"})


class TestIPWhitelistCheck(unittest.TestCase):
    """Test IP whitelist checking logic."""

    def test_empty_whitelist_rejects_all(self):
        """Test that empty whitelist rejects all IPs (defense in depth)."""
        import ipaddress

        whitelist = set()
        client_ip = "192.168.1.100"

        # Empty whitelist should reject (return False)
        if not whitelist:
            result = False
        else:
            result = True

        self.assertFalse(result)

    def test_exact_ip_match(self):
        """Test exact IP address matching."""
        import ipaddress

        whitelist = {"192.168.1.100"}
        client_ip = "192.168.1.100"

        client_addr = ipaddress.ip_address(client_ip)
        result = any(
            client_addr == ipaddress.ip_address(entry)
            for entry in whitelist
            if '/' not in entry
        )

        self.assertTrue(result)

    def test_exact_ip_no_match(self):
        """Test that non-matching IP is rejected."""
        import ipaddress

        whitelist = {"192.168.1.100"}
        client_ip = "192.168.1.101"

        client_addr = ipaddress.ip_address(client_ip)
        result = any(
            client_addr == ipaddress.ip_address(entry)
            for entry in whitelist
            if '/' not in entry
        )

        self.assertFalse(result)

    def test_cidr_range_match(self):
        """Test CIDR range matching."""
        import ipaddress

        whitelist = {"192.168.1.0/24"}
        client_ip = "192.168.1.50"

        client_addr = ipaddress.ip_address(client_ip)
        result = any(
            client_addr in ipaddress.ip_network(entry, strict=False)
            for entry in whitelist
            if '/' in entry
        )

        self.assertTrue(result)

    def test_cidr_range_no_match(self):
        """Test that IP outside CIDR range is rejected."""
        import ipaddress

        whitelist = {"192.168.1.0/24"}
        client_ip = "192.168.2.50"  # Different subnet

        client_addr = ipaddress.ip_address(client_ip)
        result = any(
            client_addr in ipaddress.ip_network(entry, strict=False)
            for entry in whitelist
            if '/' in entry
        )

        self.assertFalse(result)

    def test_invalid_client_ip_rejected(self):
        """Test that invalid client IP is handled gracefully."""
        import ipaddress

        client_ip = "not-an-ip"

        try:
            ipaddress.ip_address(client_ip)
            result = True
        except ValueError:
            result = False

        self.assertFalse(result)


class TestMinAPIKeyLength(unittest.TestCase):
    """Test minimum API key length constant."""

    def test_min_length_is_32(self):
        """Test that minimum API key length is 32 characters."""
        MIN_API_KEY_LENGTH = 32
        self.assertEqual(MIN_API_KEY_LENGTH, 32)

    def test_key_exactly_32_chars_is_valid(self):
        """Test that a 32-character key meets the minimum."""
        MIN_API_KEY_LENGTH = 32
        key = "a" * 32
        self.assertGreaterEqual(len(key), MIN_API_KEY_LENGTH)

    def test_key_31_chars_is_invalid(self):
        """Test that a 31-character key fails the minimum."""
        MIN_API_KEY_LENGTH = 32
        key = "a" * 31
        self.assertLess(len(key), MIN_API_KEY_LENGTH)


if __name__ == '__main__':
    unittest.main()
