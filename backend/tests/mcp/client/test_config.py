"""Tests for ClientConfig."""
import os
from unittest.mock import patch

import httpx
import pytest

from app.mcp.client.config import ClientConfig


class TestClientConfigDefaults:
    """Test ClientConfig default values."""

    def test_default_base_url(self):
        """Default base_url should be the oncallhealth.ai API."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClientConfig()
        assert config.base_url == "https://api.oncallhealth.ai"

    def test_default_timeouts(self):
        """Default timeout values should be sensible."""
        config = ClientConfig()
        assert config.connect_timeout == 5.0
        assert config.read_timeout == 30.0
        assert config.write_timeout == 10.0
        assert config.pool_timeout == 5.0

    def test_default_connection_limits(self):
        """Default connection pool settings."""
        config = ClientConfig()
        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.keepalive_expiry == 30.0

    def test_default_max_client_age(self):
        """Default max client age should be 4 hours."""
        config = ClientConfig()
        assert config.max_client_age_seconds == 14400  # 4 hours


class TestClientConfigFromEnv:
    """Test ClientConfig.from_env() method."""

    def test_from_env_uses_defaults_when_no_env(self):
        """from_env() should use defaults when env vars not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = ClientConfig.from_env()
        assert config.base_url == "https://api.oncallhealth.ai"
        assert config.connect_timeout == 5.0

    def test_from_env_reads_base_url(self):
        """from_env() should read ONCALLHEALTH_API_URL."""
        with patch.dict(os.environ, {"ONCALLHEALTH_API_URL": "https://custom.api.com"}):
            config = ClientConfig.from_env()
        assert config.base_url == "https://custom.api.com"

    def test_from_env_reads_timeouts(self):
        """from_env() should read timeout env vars."""
        env = {
            "ONCALLHEALTH_CONNECT_TIMEOUT": "10.0",
            "ONCALLHEALTH_READ_TIMEOUT": "60.0",
            "ONCALLHEALTH_WRITE_TIMEOUT": "20.0",
            "ONCALLHEALTH_POOL_TIMEOUT": "10.0",
        }
        with patch.dict(os.environ, env):
            config = ClientConfig.from_env()
        assert config.connect_timeout == 10.0
        assert config.read_timeout == 60.0
        assert config.write_timeout == 20.0
        assert config.pool_timeout == 10.0

    def test_from_env_reads_connection_limits(self):
        """from_env() should read connection limit env vars."""
        env = {
            "ONCALLHEALTH_MAX_CONNECTIONS": "200",
            "ONCALLHEALTH_MAX_KEEPALIVE": "40",
            "ONCALLHEALTH_KEEPALIVE_EXPIRY": "60.0",
        }
        with patch.dict(os.environ, env):
            config = ClientConfig.from_env()
        assert config.max_connections == 200
        assert config.max_keepalive_connections == 40
        assert config.keepalive_expiry == 60.0

    def test_from_env_reads_max_client_age(self):
        """from_env() should read ONCALLHEALTH_MAX_CLIENT_AGE."""
        with patch.dict(os.environ, {"ONCALLHEALTH_MAX_CLIENT_AGE": "7200"}):
            config = ClientConfig.from_env()
        assert config.max_client_age_seconds == 7200


class TestClientConfigToHttpx:
    """Test httpx conversion methods."""

    def test_to_httpx_timeout(self):
        """to_httpx_timeout() should return correctly configured Timeout."""
        config = ClientConfig(
            connect_timeout=3.0,
            read_timeout=15.0,
            write_timeout=8.0,
            pool_timeout=2.0,
        )
        timeout = config.to_httpx_timeout()

        assert isinstance(timeout, httpx.Timeout)
        assert timeout.connect == 3.0
        assert timeout.read == 15.0
        assert timeout.write == 8.0
        assert timeout.pool == 2.0

    def test_to_httpx_limits(self):
        """to_httpx_limits() should return correctly configured Limits."""
        config = ClientConfig(
            max_connections=50,
            max_keepalive_connections=10,
            keepalive_expiry=15.0,
        )
        limits = config.to_httpx_limits()

        assert isinstance(limits, httpx.Limits)
        assert limits.max_connections == 50
        assert limits.max_keepalive_connections == 10
        assert limits.keepalive_expiry == 15.0
