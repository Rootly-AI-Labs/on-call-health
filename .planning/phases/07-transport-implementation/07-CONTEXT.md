# Phase 7: Transport Implementation - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement SSE and Streamable HTTP transport endpoints for the MCP protocol, enabling remote client connections to the database-free MCP server.

**In scope:**
- Streamable HTTP endpoint at `/mcp` for Claude Desktop (current MCP spec)
- SSE endpoint at `/sse` for backward compatibility with older clients
- API key authentication for both transports
- Heartbeat mechanism to keep connections alive across proxy timeouts
- Health check endpoint at `/health` for load balancer integration
- CORS headers for web-based MCP clients

**Out of scope:**
- stdio transport (legacy local-only mode, not needed for hosted deployment)
- WebSocket transport (not part of MCP spec)
- Changes to MCP tool functionality (tools are stable from Phase 6)
- Rate limiting and connection limits (Phase 9)
- Monitoring and metrics (deferred to post-v1.1)

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User has delegated ALL implementation decisions to Claude for this transport layer. Key areas where Claude will make decisions during planning/research:

- **Endpoint routing**: Where to mount `/mcp` and `/sse` endpoints, URL structure, path conventions
- **Authentication flow**: When to validate API keys (connection-time vs per-message), header-based vs query param
- **Heartbeat strategy**: Interval timing (default 30s per requirements), message format, client/server responsibility
- **Connection lifecycle**: Timeout handling, reconnection strategy, graceful shutdown, cleanup
- **CORS configuration**: Allowed origins (localhost for development, production domains), credentials handling, preflight optimization
- **Error responses**: How to communicate transport-level errors vs protocol-level errors
- **Health check implementation**: What to verify (service ready, dependencies healthy), response format
- **FastMCP integration**: How to leverage FastMCP library's SSE/Streamable HTTP support vs custom implementation

**Constraints from requirements:**
- Must support Streamable HTTP at `/mcp` - TRANS-01
- Must support SSE at `/sse` for backward compatibility - TRANS-02
- Must send heartbeat every 30 seconds to prevent proxy timeouts - TRANS-03
- Must provide health check at `/health` - TRANS-04
- Must validate API keys for authentication - TRANS-05
- Must include CORS headers for web clients - TRANS-06

**Research focus areas:**
- FastMCP library's built-in SSE and Streamable HTTP transport support
- MCP protocol specification for transport requirements
- Existing `_resolve_asgi_app()` implementation in server.py (updated in 06-02)
- Heartbeat message format and timing recommendations
- CORS best practices for MCP endpoints
- Health check patterns for containerized services (AWS ECS readiness)

</decisions>

<specifics>
## Specific Ideas

No specific requirements — implementation should follow MCP protocol specification and FastMCP library patterns.

**Key integration points:**
- MCP server already uses FastMCP (`backend/app/mcp/server.py`)
- API key authentication exists via `extract_api_key_header()` from Phase 4
- Server is database-free from Phase 6 (deployable without DATABASE_URL)
- Will be deployed to AWS ECS/Fargate (Phase 11) - health check needed for ALB

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-transport-implementation*
*Context gathered: 2026-02-03*
