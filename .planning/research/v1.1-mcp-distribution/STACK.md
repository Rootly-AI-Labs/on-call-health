# Stack Research: SSE MCP Server Distribution and PyPI Packaging

**Domain:** MCP Server Distribution (SSE transport + PyPI packaging)
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

This research identifies the stack additions needed to transform the existing On-Call Health MCP server (stdio transport, direct DB access) into a distributable package supporting:
1. **SSE-hosted endpoint** at `mcp.oncallhealth.com/sse` for SaaS users
2. **PyPI distribution** for self-hosted/developer use via `uvx on-call-health-mcp`

The existing FastMCP library already supports SSE transport. The main work involves:
- Adding Streamable HTTP transport (recommended over SSE for new deployments)
- Creating REST API client layer to replace direct database access
- Packaging for PyPI with proper entry points

## Recommended Stack

### Core MCP Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| fastmcp | ^2.14.4 | MCP server framework | Already in use. Supports stdio, SSE, and Streamable HTTP. Latest version (Jan 2026) includes production-ready HTTP deployment features. |
| mcp | ^1.26.0 | Official MCP SDK | Provides SSE transport primitives (`sse_app()`, SSE client). FastMCP depends on this. |

**Source:** [FastMCP PyPI](https://pypi.org/project/fastmcp/) - v2.14.4 (Jan 22, 2026), [MCP PyPI](https://pypi.org/project/mcp/) - v1.26.0 (Jan 24, 2026)

### HTTP Transport Integration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| sse-starlette | ^3.2.0 | SSE for Starlette/FastAPI | Production-ready W3C SSE implementation. Native FastAPI integration. Used by FastMCP internally. |
| fastmcp-mount | ^0.1.0 | Fix path routing when mounting | Solves critical bug: FastMCP's `sse_app()` returns wrong `/messages/` path when mounted at sub-paths like `/mcp`. Required for mounting in existing FastAPI app. |

**Source:** [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) - v3.2.0 (Jan 17, 2026), [fastmcp-mount GitHub](https://github.com/dwayn/fastmcp-mount) - v0.1.0 (May 2025)

### REST API Client Layer

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| httpx | ^0.28.1 | Async HTTP client | Already in requirements.txt. Modern, async-first, requests-compatible API. Supports HTTP/2, connection pooling. Best for making REST calls to oncallhealth.ai API. |

**Why httpx over aiohttp:** httpx provides cleaner async/sync dual API, better type hints, and is already a dependency. aiohttp is also in requirements.txt but httpx is preferred for new code due to simpler ergonomics.

**Source:** [HTTPX Docs](https://www.python-httpx.org/), [httpx PyPI](https://pypi.org/project/httpx/) - v0.28.1 (Dec 2024)

### PyPI Packaging

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| hatchling | ^1.26+ | Build backend | Modern, fast, minimal configuration. Used by major Python projects. Better than setuptools for new packages. |
| build | latest | Build frontend | PEP 517 compliant build tool. Standard way to build packages. |
| twine | latest | PyPI upload | Secure HTTPS uploads to PyPI. Standard tool for publishing. |

**Why hatchling over setuptools:** Hatchling is the modern standard (2026), requires less configuration, faster builds, and better pyproject.toml support. setuptools still works but is more verbose.

**Source:** [Python Packaging Guide](https://packaging.python.org/tutorials/packaging-projects/), [State of Python Packaging 2026](https://learn.repoforge.io/posts/the-state-of-python-packaging-in-2026/)

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| uv | Package management | Replaces pip, pipx, virtualenv. Use `uvx` for tool execution. |
| pytest | Testing | Already in use |
| pytest-asyncio | Async test support | For testing async HTTP client code |
| pytest-httpx | HTTP mocking | Mock httpx requests in tests |

## Transport Strategy: Streamable HTTP + SSE Fallback

### Recommendation: Use Streamable HTTP as Primary

The MCP specification deprecated SSE in favor of Streamable HTTP (protocol version 2025-03-26). However, for backward compatibility with existing MCP clients, support both.

**Streamable HTTP advantages:**
- Single HTTP endpoint (not two like SSE)
- Stateless operation supported
- Infrastructure-friendly (works with standard HTTP proxies/load balancers)
- Session recovery on disconnect
- Future-proof (MCP's recommended transport)

**SSE still needed because:**
- Claude Desktop and some MCP clients may not support Streamable HTTP yet
- Backward compatibility during transition period

### Implementation Pattern

```python
from fastmcp import FastMCP
from fastmcp_mount import MountFastMCP

# Create MCP server with stateless HTTP for horizontal scaling
mcp = FastMCP("On-Call Health", stateless_http=True)

# For existing FastAPI app integration:
# Option 1: HTTP (Streamable) - recommended for new clients
http_app = mcp.http_app(path="/")

# Option 2: SSE - for backward compatibility
sse_app = mcp.sse_app()

# Mount in existing FastAPI app
from fastapi import FastAPI
api = FastAPI(lifespan=http_app.lifespan)  # Critical: pass lifespan

# Mount both transports
api.mount("/mcp", http_app)  # Streamable HTTP at /mcp
api.mount("/sse", MountFastMCP(app=sse_app))  # SSE at /sse (with path fix)
```

**Source:** [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http), [SSE vs Streamable HTTP](https://brightdata.com/blog/ai/sse-vs-streamable-http)

## PyPI Package Structure

### pyproject.toml Configuration

```toml
[build-system]
requires = ["hatchling >= 1.26"]
build-backend = "hatchling.build"

[project]
name = "on-call-health-mcp"
version = "0.1.0"
description = "MCP server for On-Call Health burnout analysis"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
    { name = "On-Call Health", email = "support@oncallhealth.ai" }
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
]
dependencies = [
    "fastmcp>=2.14.0",
    "httpx>=0.28.0",
    "pydantic>=2.0.0",
]

[project.scripts]
on-call-health-mcp = "on_call_health_mcp.cli:main"

[project.urls]
Homepage = "https://oncallhealth.ai"
Documentation = "https://docs.oncallhealth.ai/mcp"
Repository = "https://github.com/on-call-health/mcp-server"
Issues = "https://github.com/on-call-health/mcp-server/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/on_call_health_mcp"]
```

### Entry Point for uvx

The `[project.scripts]` entry creates the CLI command that enables:
```bash
uvx on-call-health-mcp --api-key och_live_xxx
```

**Source:** [Python Packaging Guide - Scripts](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

## REST API Client Architecture

### Replace Direct DB with REST Calls

Current MCP server does direct database queries:
```python
# Current (direct DB)
analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
```

New architecture uses REST API calls:
```python
# New (REST API via httpx)
async with httpx.AsyncClient(base_url="https://api.oncallhealth.ai") as client:
    response = await client.get(
        f"/analyses/{analysis_id}",
        headers={"X-API-Key": api_key}
    )
    analysis = response.json()
```

### Recommended httpx Patterns

```python
import httpx
from contextlib import asynccontextmanager

class OnCallHealthClient:
    """REST API client for On-Call Health API."""

    def __init__(self, api_key: str, base_url: str = "https://api.oncallhealth.ai"):
        self.api_key = api_key
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    @asynccontextmanager
    async def _get_client(self):
        """Get or create httpx client with connection pooling."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"X-API-Key": self.api_key},
                timeout=30.0,
            )
        yield self._client

    async def get_analysis(self, analysis_id: int) -> dict:
        async with self._get_client() as client:
            response = await client.get(f"/analyses/{analysis_id}")
            response.raise_for_status()
            return response.json()

    async def start_analysis(self, days_back: int = 30) -> dict:
        async with self._get_client() as client:
            response = await client.post(
                "/analysis/start",
                json={"days_back": days_back}
            )
            response.raise_for_status()
            return response.json()

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
```

**Best Practices Applied:**
- Single shared client instance (connection pooling)
- Explicit timeouts
- Context manager for resource cleanup
- Type hints throughout

**Source:** [HTTPX Async Guide](https://www.python-httpx.org/async/), [httpx Best Practices](https://betterstack.com/community/guides/scaling-python/httpx-explained/)

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Streamable HTTP | SSE only | Only if all clients are legacy SSE-only |
| httpx | aiohttp | If you need WebSocket support in same client |
| hatchling | setuptools | If you need C extension compilation support |
| fastmcp-mount | Manual path fixing | Never - the middleware is cleaner |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| SSE-only transport | Deprecated by MCP spec; scaling issues with load balancers | Streamable HTTP + SSE fallback |
| requests library | Sync-only, no HTTP/2 | httpx (async, HTTP/2) |
| setup.py | Legacy, more verbose | pyproject.toml with hatchling |
| Direct DB access in PyPI package | Package shouldn't have DB dependency | REST API client layer |
| poetry for build | Good tool but hatchling is simpler for pure packages | hatchling |

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| fastmcp>=2.14.0 | mcp>=1.26.0 | FastMCP 2.x requires MCP SDK 1.x |
| fastmcp>=2.14.0 | Python 3.10+ | Both require Python 3.10 minimum |
| httpx>=0.28.0 | Python 3.8+ | Broader compatibility than MCP |
| sse-starlette>=3.2.0 | Python 3.9+ | One version higher than httpx minimum |

**Overall minimum:** Python 3.10 (driven by FastMCP/MCP SDK requirements)

## Installation Commands

### For Hosted SSE Server (backend changes)

```bash
# No new packages needed - fastmcp already supports SSE
# Just add fastmcp-mount for path fixing
pip install fastmcp-mount>=0.1.0
```

### For PyPI Package Development

```bash
# Build tools
pip install build twine

# Development dependencies
pip install pytest pytest-asyncio pytest-httpx

# Or with uv (recommended)
uv pip install build twine
uv pip install pytest pytest-asyncio pytest-httpx
```

### For End Users (after PyPI publish)

```bash
# One-time execution (ephemeral)
uvx on-call-health-mcp --api-key och_live_xxx

# Or install globally
uv tool install on-call-health-mcp
on-call-health-mcp --api-key och_live_xxx
```

## Authentication Strategy

### API Key Authentication (Existing)

The current MCP server already uses API key auth via `X-API-Key` header. This works for:
- Stdio transport (API key from environment: `OCH_API_KEY`)
- HTTP/SSE transport (API key in request header)

### For Hosted SSE Endpoint

FastMCP supports built-in authentication:

```python
from fastmcp.server.auth import BearerTokenAuth
import os

# Use API key as bearer token for simplicity
auth = BearerTokenAuth(token=os.environ.get("MCP_AUTH_TOKEN"))
mcp = FastMCP("On-Call Health", auth=auth)
```

Or keep the existing `X-API-Key` header approach and handle in middleware.

**Recommendation:** Keep existing `X-API-Key` pattern for consistency with REST API. Handle in custom middleware rather than FastMCP's built-in auth.

## Sources

### HIGH Confidence (Official Documentation)

- [FastMCP PyPI](https://pypi.org/project/fastmcp/) - v2.14.4, verified Jan 2026
- [MCP Python SDK PyPI](https://pypi.org/project/mcp/) - v1.26.0, verified Jan 2026
- [FastMCP HTTP Deployment Guide](https://gofastmcp.com/deployment/http)
- [Python Packaging User Guide](https://packaging.python.org/tutorials/packaging-projects/)
- [HTTPX Official Docs](https://www.python-httpx.org/)
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) - v3.2.0

### MEDIUM Confidence (Verified with Multiple Sources)

- [SSE vs Streamable HTTP Comparison](https://brightdata.com/blog/ai/sse-vs-streamable-http)
- [MCP Transport Protocols Guide](https://mcpcat.io/guides/comparing-stdio-sse-streamablehttp/)
- [fastmcp-mount GitHub](https://github.com/dwayn/fastmcp-mount)
- [State of Python Packaging 2026](https://learn.repoforge.io/posts/the-state-of-python-packaging-in-2026/)
- [uv Documentation](https://docs.astral.sh/uv/)

---
*Stack research for: SSE MCP Server Distribution and PyPI Packaging*
*Researched: 2026-02-02*
