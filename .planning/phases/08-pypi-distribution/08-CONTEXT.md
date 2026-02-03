# Phase 8: PyPI Distribution - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Package the MCP server for distribution via PyPI, enabling users to install with `pip install oncallhealth-mcp` and run with `uvx oncallhealth-mcp`. This makes the MCP server self-hostable without cloning the repository.

**In scope:**
- PyPI-publishable package structure with pyproject.toml
- CLI entry point for running the MCP server
- Support for uvx execution (zero-installation run)
- Environment variable configuration (API key, API URL)
- README with installation and setup instructions
- Transport selection via CLI flag (stdio vs HTTP)

**Out of scope:**
- New MCP tool functionality (tools are stable from Phase 6)
- Hosted endpoint deployment (Phase 11 - AWS)
- Rate limiting and connection limits (Phase 9 - Infrastructure)
- User documentation beyond README (Phase 10 - Documentation)
- Publishing to PyPI (manual step after package creation)

</domain>

<decisions>
## Implementation Decisions

### Package Structure and Naming

**Package name: `oncallhealth-mcp`**
- User decision: Clear branding with MCP suffix
- Install command: `pip install oncallhealth-mcp`
- Run command: `uvx oncallhealth-mcp` or `python -m oncallhealth_mcp`

**Code structure: Standalone package (copy MCP code)**
- User decision: Duplicate backend/app/mcp/ into new package directory
- Completely independent from main web application
- Single source of truth for PyPI distribution
- Package lives in its own directory (e.g., `packages/oncallhealth-mcp/` or root-level)

**Package contents: Claude's discretion**
- User delegated to Claude: Determine minimal dependencies needed for working MCP server
- Must include: backend/app/mcp/ code (server, transport, client, normalizers, auth)
- Exclude: Web app code, database models, FastAPI routes unrelated to MCP

### CLI Interface Design

**Command name: `oncallhealth-mcp`**
- User decision: Matches package name
- Usage: `uvx oncallhealth-mcp` or `oncallhealth-mcp` (if pip installed)

**Transport selection: CLI flag**
- User decision: `oncallhealth-mcp --transport=http` or `--transport=stdio`
- Single entry point with transport flag
- Default transport: Claude's discretion (likely stdio for backward compat or http for modern)

**Configuration approach: Claude's discretion**
- User delegated to Claude: Choose between env vars only vs CLI flags + env vars
- Must support: ONCALLHEALTH_API_KEY, ONCALLHEALTH_API_URL (or similar)
- Consider: MCP server conventions, ease of use, flexibility

### Claude's Discretion (Additional Areas)

User has delegated these decisions to Claude during planning/research:

- **Python version support**: Minimum Python version (3.10+, 3.11+?)
- **Dependency management**: Pin exact versions or allow ranges, optional dependencies for transports
- **Module structure**: Flat vs nested, __main__.py location, entry point setup
- **Development dependencies**: Whether to include dev/test dependencies or separate them
- **pyproject.toml configuration**: Build system (hatchling, poetry, setuptools), metadata fields
- **README content**: Installation steps, configuration examples, troubleshooting, uvx vs pip guidance
- **Error handling**: Validation for missing API key, invalid config, connection errors
- **Logging configuration**: Default log level, log format, how to adjust verbosity

**Constraints from requirements:**
- Must support `pip install oncallhealth-mcp` - PYPI-01
- Must support `uvx oncallhealth-mcp` execution - PYPI-03
- Must allow transport selection (stdio vs HTTP) - PYPI-04
- Must configure via environment variables - PYPI-05
- README must provide clear installation/setup - PYPI-06, PYPI-07
- Must work with API_KEY environment variable - PYPI-02

**Research focus areas:**
- PyPI packaging best practices (pyproject.toml structure, build systems)
- uvx compatibility requirements (entry point configuration)
- Existing MCP server CLI patterns (mcp-server-*, fastmcp examples)
- Python package structure for installable servers
- Environment variable conventions in MCP ecosystem
- Existing backend/app/mcp/ code dependencies and imports

</decisions>

<specifics>
## Specific Ideas

**User preferences:**
- Package name: `oncallhealth-mcp`
- Command name: `oncallhealth-mcp` (matches package)
- Code structure: Standalone (copy backend/app/mcp/)
- Transport selection: Flag-based (`--transport=http` or `--transport=stdio`)

**Integration points:**
- Phase 5: REST API Client (OnCallHealthClient must be included)
- Phase 6: Refactored MCP tools (all tools use REST, no DB dependency)
- Phase 7: Transport layer (mcp_http_app for HTTP, FastMCP for stdio)
- Existing backend/app/mcp/ module structure

**Key files to package:**
- backend/app/mcp/server.py - MCP server with tools
- backend/app/mcp/transport.py - HTTP/SSE transport layer
- backend/app/mcp/client/ - REST API client (OnCallHealthClient)
- backend/app/mcp/normalizers.py - Response transformers
- backend/app/mcp/auth.py - API key extraction
- backend/app/mcp/serializers.py - Datetime serialization helpers

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 08-pypi-distribution*
*Context gathered: 2026-02-03*
