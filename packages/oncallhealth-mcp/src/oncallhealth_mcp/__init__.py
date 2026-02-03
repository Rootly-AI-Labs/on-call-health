"""
oncallhealth-mcp: MCP server for On-Call Health burnout analysis.

This package provides an MCP (Model Context Protocol) server that enables
AI assistants to access On-Call Health burnout analysis features.

Usage:
    # Run via uvx (recommended)
    uvx oncallhealth-mcp

    # Or as a module
    python -m oncallhealth_mcp

    # Or via console script after pip install
    oncallhealth-mcp

Configuration:
    ONCALLHEALTH_API_KEY: Your On-Call Health API key (required)
    ONCALLHEALTH_API_URL: API base URL (default: https://api.oncallhealth.ai)
"""

__version__ = "0.1.0"

# Convenience exports
from oncallhealth_mcp.server import mcp_server
from oncallhealth_mcp.client import OnCallHealthClient, ClientConfig

__all__ = [
    "__version__",
    "mcp_server",
    "OnCallHealthClient",
    "ClientConfig",
]
