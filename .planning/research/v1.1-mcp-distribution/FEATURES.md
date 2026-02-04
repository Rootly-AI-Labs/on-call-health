# Feature Research: MCP Server Distribution

**Domain:** SSE-hosted MCP servers and PyPI-distributed packages
**Researched:** 2026-02-02
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

#### SSE/Streamable HTTP Transport

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **SSE endpoint at `/sse`** | Standard MCP convention (Rootly, community servers use this path) | LOW | FastMCP provides `sse_app()` for mounting |
| **Streamable HTTP endpoint** | MCP spec (2025-03-26+) recommends this over pure SSE | MEDIUM | FastMCP provides `streamable_http_app()`, newer standard |
| **Health check endpoint (`/health`)** | Load balancers, Kubernetes need to verify server is alive | LOW | Return `{"status": "ok"}` with 200 |
| **Graceful connection handling** | Connections drop; server must not crash or leak resources | MEDIUM | Handle client disconnects, implement timeouts |
| **Authorization header support** | MCP clients pass API keys via `Authorization: Bearer <token>` | LOW | Already supported via existing auth.py |
| **CORS configuration** | Browser-based MCP clients need cross-origin access | LOW | FastAPI/Starlette middleware |
| **Connection timeout (60s heartbeat)** | Proxies close idle connections after 60s per HTTP/1.1 spec | MEDIUM | Send periodic ping events every 30s |

#### PyPI Package Distribution

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **`uvx` support** | Standard way to run MCP servers without install (mcp-server-git pattern) | LOW | Package with entry point in pyproject.toml |
| **Console script entry point** | `uvx on-call-health-mcp` should work | LOW | `[project.scripts]` in pyproject.toml |
| **`--help` flag with usage** | Users need to see available options | LOW | argparse or click |
| **Environment variable config** | `OCH_API_KEY` for auth, standard pattern | LOW | Read from env, document clearly |
| **Both transports (stdio default)** | stdio for local (Claude Desktop), SSE for hosted | LOW | `--transport` flag or env var |
| **Clear error messages** | "Missing API key" not "NoneType has no attribute" | LOW | Validate config on startup |
| **README with quickstart** | PyPI page must show how to use | LOW | Include in package metadata |

#### REST API Client Layer

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Retry with exponential backoff** | Network errors are transient; blind retries cause thundering herd | MEDIUM | 3-5 retries, 2^n + jitter pattern |
| **Timeout configuration** | Prevent hanging on slow responses | LOW | httpx defaults to 5s, make configurable |
| **Bearer token authentication** | Pass API key to oncallhealth.ai backend | LOW | `Authorization: Bearer {api_key}` header |
| **Error mapping (HTTP -> MCP)** | 401 -> auth error, 429 -> rate limit, 500 -> server error | MEDIUM | Translate HTTP codes to MCP error codes |
| **Base URL configuration** | Allow pointing to different environments (staging, local) | LOW | Env var `OCH_API_URL` |

#### Documentation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Claude Desktop config example** | Most common MCP client | LOW | JSON snippet in docs |
| **Cursor/VS Code config example** | Second most common clients | LOW | JSON snippets |
| **API key setup instructions** | Link to oncallhealth.ai API key page | LOW | Step-by-step guide |
| **Troubleshooting section** | "Connection refused", "401 Unauthorized" etc. | LOW | FAQ format |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Zero-install SSE endpoint** | `https://mcp.oncallhealth.com/sse` works without any local setup | MEDIUM | Matches Rootly pattern, significant UX advantage |
| **Dual transport flexibility** | Same package works for SaaS (SSE) and self-hosted (stdio) | LOW | Transport abstraction already in mcp SDK |
| **Automatic reconnection guidance** | MCP clients often lose connections; provide clear recovery | LOW | Document reconnection, implement progress tokens |
| **Readiness probe (`/health/ready`)** | Distinguish "alive" from "ready to serve" (database connected, etc.) | LOW | Kubernetes best practice |
| **Connection limit per user** | Prevent single user from exhausting server resources | MEDIUM | Track active SSE connections per API key |
| **Request ID correlation** | Pass X-Request-ID through REST calls for debugging | LOW | Include in API client headers |
| **Structured logging** | JSON logs with request_id, user_id, tool_name for observability | LOW | Use existing visual_logger patterns |
| **`--version` flag** | Show package version for debugging | LOW | Read from package metadata |
| **Progress notifications** | Long-running tools (analysis_start) report progress | MEDIUM | MCP progress tokens via notifications |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **WebSocket transport** | "More efficient than SSE" | Not in MCP spec, no client support, complexity without benefit | Use Streamable HTTP (MCP standard) |
| **Direct database mode for SSE** | "Lower latency" | Security risk (DB credentials in hosted env), breaks architecture | REST API only, accept ~50ms latency |
| **Automatic key refresh** | "Handle expired tokens transparently" | Hides auth errors, confusing debug experience, silent failures | Fail fast with clear error, user refreshes key |
| **Embedded web UI** | "Let me manage keys from MCP server" | Scope creep, security complexity, already exists at oncallhealth.ai | Link to web UI in error messages |
| **Multi-tenant SSE** | "Different orgs on same endpoint" | Complexity, isolation concerns, harder debugging | One endpoint per deployment |
| **Caching layer in MCP server** | "Cache analysis results" | Stale data issues, cache invalidation complexity, oncallhealth.ai already caches | Let backend handle caching |
| **OAuth flow in PyPI package** | "Let users login from CLI" | Complex device flow, security risks, existing web login works | API keys only (created via web UI) |
| **HTTP/2 push** | "Server can push without request" | Not widely supported by MCP clients, complexity | SSE heartbeats sufficient |
| **Unlimited connections** | "Don't restrict users" | Resource exhaustion, DoS vector, unfair to other users | Reasonable limits (5-10 connections per key) |
| **Real-time SSE metrics** | "Show connection count, throughput" | Observability infrastructure scope creep | Use existing monitoring (NewRelic) |

## Feature Dependencies

```
[REST API Client]
    |
    v
[MCP Server (Refactored)]
    |
    +---> [stdio transport] <--- PyPI package
    |
    +---> [SSE/Streamable HTTP transport] <--- Hosted endpoint

[PyPI Package]
    |--requires---> [Console script entry point]
    |--requires---> [Environment variable config]
    |--requires---> [REST API Client]
    |--requires---> [--help documentation]

[Hosted SSE Endpoint]
    |--requires---> [Health check endpoints]
    |--requires---> [Connection timeout handling]
    |--requires---> [CORS configuration]
    |--requires---> [REST API Client]
    |--requires---> [Rate limiting (existing)]

[REST API Client]
    |--requires---> [httpx async client]
    |--requires---> [Retry logic]
    |--requires---> [Error mapping]
    |--requires---> [Base URL config]

[Documentation]
    |--requires---> [PyPI package published]
    |--requires---> [SSE endpoint deployed]
```

### Dependency Notes

- **REST API Client must exist before MCP refactor:** Server needs to call oncallhealth.ai APIs
- **Both transports share REST API Client:** Code reuse, single implementation
- **Health checks independent of MCP:** Standard HTTP endpoints, can add first
- **Documentation follows implementation:** Can't document what doesn't exist yet
- **PyPI package can exist without SSE:** stdio-only release is valid first step

## MVP Definition

### Launch With (v1.1)

Minimum viable product - what's needed for zero-install MCP access.

- [ ] **REST API client layer** - httpx with retry, timeout, error mapping
- [ ] **SSE transport endpoint (`/sse`)** - FastMCP sse_app() mounted on FastAPI
- [ ] **Health check (`/health`)** - Basic liveness probe
- [ ] **Connection heartbeat (30s ping)** - Prevent proxy timeout
- [ ] **PyPI package `on-call-health-mcp`** - Published with uvx support
- [ ] **Console script entry point** - `uvx on-call-health-mcp`
- [ ] **Environment variable config** - `OCH_API_KEY`, `OCH_API_URL`
- [ ] **stdio transport (default)** - For Claude Desktop and local use
- [ ] **`--transport` flag** - Choose stdio or sse
- [ ] **`--help` flag** - Show usage
- [ ] **Claude Desktop config example** - In README and docs
- [ ] **Error messages for common failures** - Auth, network, rate limit
- [ ] **MCP tools via REST API** - analysis_start, analysis_status, analysis_results, analysis_current, integrations_list

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] **Streamable HTTP transport** - When MCP clients adopt it widely
- [ ] **Readiness probe (`/health/ready`)** - When Kubernetes deployment needed
- [ ] **Connection limit per API key** - When abuse detected
- [ ] **Progress notifications** - When users request long-running feedback
- [ ] **`--version` flag** - When debugging version issues arises
- [ ] **Cursor/VS Code config examples** - When user requests come in
- [ ] **Request ID correlation** - When debugging cross-service issues

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Additional MCP clients documentation** - Wait for ecosystem to stabilize
- [ ] **Custom timeout configuration** - Default works for most cases
- [ ] **Connection metrics** - Use existing NewRelic for now
- [ ] **Multiple API key rotation** - Users can create new key, revoke old

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| REST API client layer | HIGH | MEDIUM | P1 |
| SSE endpoint (`/sse`) | HIGH | LOW | P1 |
| PyPI package | HIGH | LOW | P1 |
| stdio transport | HIGH | LOW | P1 |
| Health check | HIGH | LOW | P1 |
| Connection heartbeat | HIGH | LOW | P1 |
| `--help` flag | MEDIUM | LOW | P1 |
| Environment config | MEDIUM | LOW | P1 |
| Claude Desktop docs | MEDIUM | LOW | P1 |
| Error messages | MEDIUM | LOW | P1 |
| `--transport` flag | MEDIUM | LOW | P1 |
| Readiness probe | LOW | LOW | P2 |
| Connection limits | MEDIUM | MEDIUM | P2 |
| Progress notifications | LOW | MEDIUM | P2 |
| Streamable HTTP | LOW | MEDIUM | P3 |
| Request ID correlation | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Rootly MCP | Brave Search MCP | mcp-server-git | Our Approach |
|---------|------------|------------------|----------------|--------------|
| Hosted SSE endpoint | `https://mcp.rootly.com/sse` | Community only (Shoofio) | No (stdio only) | `https://mcp.oncallhealth.com/sse` |
| PyPI distribution | Yes (`uvx rootly-mcp-server`) | No (npm only) | Yes (`uvx mcp-server-git`) | Yes (`uvx on-call-health-mcp`) |
| Auth method | Bearer token | API key (env var) | N/A (local git) | Bearer token (API key) |
| Transports | SSE + stdio | stdio (HTTP optional) | stdio only | SSE + stdio |
| Smart pagination | Yes (10 items default) | N/A | N/A | N/A (not needed for our tools) |
| Dynamic tool generation | Yes (from OpenAPI) | No (fixed tools) | No (fixed tools) | No (fixed tools, simpler) |
| Health endpoint | Unknown | Unknown | No | Yes (`/health`) |
| Progress notifications | Unknown | Unknown | No | Future (v1.x) |

## Technical Considerations

### Transport Protocol Decision

**Recommendation:** Support both SSE (legacy) and Streamable HTTP (future)

SSE was deprecated in MCP spec (2025-03-26) but remains widely supported. Streamable HTTP is the new standard. FastMCP supports both via `sse_app()` and `streamable_http_app()`.

**For v1.1:** Start with SSE (maximum client compatibility), document path to Streamable HTTP.

Source: [MCP Transports Documentation](https://modelcontextprotocol.io/legacy/concepts/transports), [Why MCP Deprecated SSE](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/)

### REST API Client Library

**Recommendation:** Use `httpx` with `AsyncClient`

- Built-in async support (required for MCP async handlers)
- Connection pooling for performance
- Built-in retry via `httpx.AsyncHTTPTransport(retries=N)`
- Timeout configuration at client level
- HTTP/2 support if needed

Source: [HTTPX Documentation](https://www.python-httpx.org/), [8 httpx Patterns for Safer Clients](https://medium.com/@sparknp1/8-httpx-asyncio-patterns-for-safer-faster-clients-f27bc82e93e6)

### Error Code Mapping

| HTTP Status | MCP Error Code | User Message |
|-------------|----------------|--------------|
| 401 | -32001 (authentication) | "Invalid or expired API key" |
| 403 | -32003 (forbidden) | "API key does not have permission" |
| 404 | -32002 (not found) | "Resource not found" |
| 429 | -32004 (rate limited) | "Rate limit exceeded, retry after {N}s" |
| 500+ | -32005 (internal error) | "Server error, please try again" |

### Connection Timeout Strategy

**Problem:** HTTP proxies (Nginx, Cloudflare) close idle connections after 60 seconds.

**Solution:** Send SSE comment event (`:ping`) every 30 seconds.

```python
async def sse_heartbeat():
    while True:
        yield ": ping\n\n"
        await asyncio.sleep(30)
```

Source: [MCP Server Timeout Issues](https://github.com/anthropics/claude-code/issues/3033), [SSE Best Practices](https://mcp-cloud.ai/docs/sse-protocol/best-practices)

### Package Structure

```
on-call-health-mcp/
|-- pyproject.toml
|-- README.md
|-- src/
|   |-- on_call_health_mcp/
|       |-- __init__.py
|       |-- __main__.py       # Entry point for python -m
|       |-- cli.py            # argparse CLI
|       |-- server.py         # MCP server (tools, resources)
|       |-- api_client.py     # REST API client (httpx)
|       |-- config.py         # Environment variable handling
```

pyproject.toml entry points:
```toml
[project.scripts]
on-call-health-mcp = "on_call_health_mcp.cli:main"
```

Source: [mcp-server-git Package](https://pypi.org/project/mcp-server-git/), [Entry Points Specification](https://packaging.python.org/specifications/entry-points/)

## Sources

### MCP Protocol & Transports
- [MCP Transports Documentation](https://modelcontextprotocol.io/legacy/concepts/transports)
- [Streamable HTTP Transport](https://brightdata.com/blog/ai/sse-vs-streamable-http)
- [Why MCP Deprecated SSE](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/)
- [MCP Python SDK](https://pypi.org/project/mcp/)

### Reference Implementations
- [Rootly MCP Server Documentation](https://docs.rootly.com/integrations/mcp-server)
- [Rootly MCP Server GitHub](https://github.com/Rootly-AI-Labs/Rootly-MCP-server)
- [mcp-server-git PyPI](https://pypi.org/project/mcp-server-git/)
- [Brave Search MCP SSE (Community)](https://github.com/Shoofio/brave-search-mcp-sse)

### Authentication & Security
- [MCP Authentication Guide](https://stytch.com/blog/MCP-authentication-and-authorization-guide/)
- [Bearer Token Best Practices (GitHub Discussion)](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions/1247)
- [API Key Security Best Practices](https://www.stainless.com/mcp/mcp-server-api-key-management-best-practices)

### Error Handling & Reliability
- [MCP Error Handling Best Practices](https://mcpcat.io/guides/error-handling-custom-mcp-servers/)
- [Timeout and Retry Strategies](https://octopus.com/blog/mcp-timeout-retry)
- [HTTPX Timeouts](https://www.python-httpx.org/advanced/timeouts/)

### Health Checks & Operations
- [MCP Health Check Endpoints](https://mcpcat.io/guides/building-health-check-endpoint-mcp-server/)
- [Production-Ready MCP Servers](https://thinhdanggroup.github.io/mcp-production-ready/)

### Configuration Patterns
- [MCP JSON Configuration](https://gofastmcp.com/integrations/mcp-json-configuration)
- [Environment Variables in MCP](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/command-line-mcp-configuration.html)

---
*Feature research for: MCP Server Distribution (v1.1)*
*Researched: 2026-02-02*
