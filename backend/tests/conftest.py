"""Pytest configuration for test suite."""
import os
import sys
from unittest.mock import MagicMock

# Set required environment variables before importing app modules
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
os.environ.setdefault("ENCRYPTION_KEY", "dGVzdC1lbmNyeXB0aW9uLWtleS1mb3ItdGVzdGluZy1vbmx5")

# Mock FastMCP before any app.mcp imports to avoid ASGI app resolution errors
mock_fastmcp_instance = MagicMock()
mock_fastmcp_instance.app = MagicMock()
mock_fastmcp_instance.tool = MagicMock(return_value=lambda f: f)
mock_fastmcp_instance.resource = MagicMock(return_value=lambda f: f)
mock_fastmcp_instance.prompt = MagicMock(return_value=lambda f: f)

mock_fastmcp_class = MagicMock(return_value=mock_fastmcp_instance)

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP = mock_fastmcp_class
