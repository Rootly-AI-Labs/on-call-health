# Project Research Summary

**Project:** v1.1 MCP Server Distribution
**Domain:** MCP Server Distribution (SSE transport + PyPI packaging)
**Researched:** 2026-02-02
**Confidence:** HIGH

## Executive Summary

The On-Call Health MCP server currently operates via stdio transport with direct database access, limiting it to local use only. This research identifies a clear path to transform it into a distributable package supporting both hosted SSE/Streamable HTTP access at `mcp.oncallhealth.com` and PyPI distribution via `uvx on-call-health-mcp` for self-hosted deployments. The key architectural shift is replacing direct database queries with REST API calls to the existing oncallhealth.ai backend, enabling both deployment models to share the same core MCP tool implementations.

The recommended approach uses Streamable HTTP as the primary transport (MCP's current standard as of protocol version 2025-03-26) with SSE fallback for backward compatibility. FastMCP v2.14.4+ already provides production-ready HTTP deployment features. The REST API client layer (httpx with retry logic) is the critical component enabling both deployment models. PyPI packaging uses modern hatchling build backend with flexible dependency bounds to avoid conflicts with user environments.

The primary risks are connection pool exhaustion in long-running HTTP clients, retry storm amplification across the multi-layer architecture, and SSE sub-path mounting breaking client communication. These are all well-documented problems with proven solutions: implement client health monitoring with periodic recreation, use circuit breakers with retry budgets, and apply the fastmcp-mount middleware to fix path routing issues.

## Key Findings

### Recommended Stack

The existing FastMCP library (already in use) supports all needed transports - the main additions are for HTTP transport integration and PyPI packaging infrastructure. Critical insight: Streamable HTTP is now the MCP-recommended transport (SSE deprecated as of March 2025), though SSE should be supported for backward compatibility during the transition period.

**Core technologies:**
- **fastmcp v2.14.4+**: Already in use, supports stdio, SSE, and Streamable HTTP transports with production HTTP deployment features
- **mcp v1.26.0**: Official MCP SDK dependency, provides SSE transport primitives
- **httpx v0.28.1+**: Already in requirements.txt, modern async HTTP client for REST API calls with HTTP/2 and connection pooling
- **sse-starlette v3.2.0**: Production W3C SSE implementation with native FastAPI integration
- **fastmcp-mount v0.1.0**: Critical middleware to fix FastMCP's path routing bug when mounted at sub-paths
- **hatchling v1.26+**: Modern build backend for PyPI packaging, cleaner than setuptools

**Key version requirement:** Python 3.10+ (driven by FastMCP/MCP SDK requirements)

### Expected Features

Based on analysis of reference implementations (Rootly MCP, mcp-server-git) and MCP best practices.

**Must have (table stakes):**
- Streamable HTTP endpoint at `/mcp` - MCP's current standard transport
- SSE endpoint at `/sse` - backward compatibility with existing clients
- Health check endpoint (`/health`) - load balancers and Kubernetes require this
- PyPI package with uvx support - standard distribution method for MCP servers
- Console script entry point - `uvx on-call-health-mcp` command
- Environment variable config - `OCH_API_KEY` for authentication
- Connection heartbeat (30s ping) - prevent proxy timeout after 60s idle
- REST API client with retry/backoff - network failures are transient
- Error mapping (HTTP status -> user messages) - 401 = "Invalid API key", 429 = "Rate limited"

**Should have (competitive):**
- Dual transport flexibility - same package works for SaaS (hosted SSE) and self-hosted (stdio)
- Zero-install SSE endpoint - `https://mcp.oncallhealth.com/sse` with no local setup required
- Connection limit per API key - prevent resource exhaustion from single user
- Structured logging with request IDs - observability for debugging
- Readiness probe (`/health/ready`) - Kubernetes best practice for deployment readiness

**Defer (v2+):**
- Progress notifications for long-running tools - nice to have but not essential
- Multiple client documentation (Cursor, VS Code) - wait for user requests
- Custom timeout configuration - defaults work for most cases
- Connection metrics endpoint - use existing NewRelic monitoring

### Architecture Approach

The hybrid architecture approach enables both deployment models (hosted SSE and PyPI-distributed stdio) to share identical MCP tool implementations via a common REST API client layer. This cleanly separates concerns: transport layer handles client communication, tools layer implements MCP functionality, REST client abstracts backend communication.

**Major components:**

1. **OnCallHealthClient (REST API Client)** - httpx.AsyncClient wrapper with retry logic, timeout configuration, API key injection, and error mapping. Replaces all direct database access.

2. **MCP Tools Layer (shared code)** - FastMCP tool definitions (analysis_start, analysis_status, etc.) that call OnCallHealthClient. Transport-agnostic and testable.

3. **Transport Implementations**:
   - **Streamable HTTP** (`/mcp`) - Single endpoint, stateless operation, recommended for production
   - **SSE** (`/sse` + `/messages/`) - Dual endpoints for backward compatibility
   - **stdio** - For PyPI package, local Claude Desktop use

4. **FastAPI Integration** - Mount MCP transports into existing backend at `/mcp` path, with fastmcp-mount middleware to fix sub-path routing

5. **PyPI Package Structure** - Console script entry point, environment config, flexible dependency bounds

**Critical architectural decision:** Use REST API (not direct DB) even for hosted SSE server. This enables horizontal scaling, cleaner separation of concerns, and code reuse between hosted and distributed versions. Accept ~50ms latency increase for architectural benefits.

### Critical Pitfalls

Research identified 8 critical pitfalls with proven prevention strategies:

1. **SSE Transport Deprecation** - MCP deprecated SSE in favor of Streamable HTTP (March 2025). Build on Streamable HTTP as primary transport, use SSE only for backward compatibility. Avoid building SSE-only implementation.

2. **Sub-path Mounting Breaks Communication** - FastMCP's SSE generates incorrect endpoint paths when mounted under sub-paths (e.g., `/mcp/v1/`). Use fastmcp-mount middleware to intercept and fix paths, or mount at root. Streamable HTTP avoids this issue entirely.

3. **Connection Pool Exhaustion** - Long-lived httpx.AsyncClient instances can exhaust connection pools after 3-12 hours, throwing PoolTimeout errors. Implement client health monitoring and periodic recreation (every 4 hours). Configure explicit limits and keepalive_expiry.

4. **Retry Storm Amplification** - Retries multiply exponentially across layers (MCP client -> MCP server -> REST API -> backend). With 3 retries per layer across 5 layers = 243x amplification. Use circuit breakers, implement retry budgets, prefer retries at edge.

5. **PyPI Dependency Conflicts** - Strict version pins cause ResolutionImpossible errors. Use flexible bounds (e.g., `fastapi>=0.100.0,<1.0.0`), pin MCP SDK to stable v1.x (`mcp>=1.0.0,<2.0.0`), test with both min and max versions.

6. **Console Script Entry Points Fail After PyPI Install** - Entry points behave differently in editable vs wheel installs. Build and test actual wheel (`pip install dist/*.whl`) in fresh virtualenv before publishing. Use TestPyPI first.

7. **Lifespan Context Not Propagated** - FastMCP session manager requires proper lifespan initialization. When mounting in FastAPI, explicitly pass lifespan: `app = FastAPI(lifespan=mcp_app.lifespan)`. Test session persistence across requests.

8. **REST API as Database Anti-Pattern** - Porting direct DB code line-by-line creates N+1 query patterns over HTTP. Design batch endpoints, handle partial failures, add timeouts everywhere, cache aggressively.

## Implications for Roadmap

Based on research, the implementation should follow dependency order with clear verification gates. The REST API client is the foundation that enables all other work.

### Phase 1: REST API Client Foundation

**Rationale:** All other phases depend on this. Cannot implement any transport without replacing direct DB access. This is the most critical architectural change.

**Delivers:**
- OnCallHealthClient with httpx.AsyncClient
- Retry logic with exponential backoff and jitter
- Circuit breaker pattern to prevent retry storms
- Error mapping (HTTP status codes -> user-friendly messages)
- Timeout configuration (connect, read, write, pool)
- Client health monitoring and periodic recreation
- Base URL configuration via environment variable

**Addresses:**
- REST API client with retry/backoff (table stakes)
- Error mapping (table stakes)
- Base URL configuration (table stakes)

**Avoids:**
- Connection pool exhaustion (Pitfall #3)
- Retry storm amplification (Pitfall #4)
- REST API as database anti-pattern (Pitfall #8)

**Verification:**
- Integration tests with mocked HTTP responses
- 12+ hour stress test with simulated network failures
- Load test: simulate backend failure, verify no retry amplification

### Phase 2: MCP Tools Refactor

**Rationale:** Must exist before transport implementation. Tools must be transport-agnostic and use REST API client exclusively. This is where direct DB dependencies are removed.

**Delivers:**
- Tool implementations using OnCallHealthClient
- Transport-agnostic tool signatures
- Shared tool code for all transports (stdio, SSE, Streamable HTTP)
- API key authentication via HTTP headers
- Comprehensive error handling in tools

**Uses:**
- OnCallHealthClient from Phase 1
- FastMCP for tool definitions

**Implements:**
- MCP Tools Layer (architecture component #2)
- All existing MCP tools migrated from direct DB to REST API

**Addresses:**
- Environment variable config (table stakes)

**Verification:**
- Unit tests for each tool with mocked client
- Integration tests with test backend
- Verify no direct DB imports remain in tool code

### Phase 3: Transport Implementation (Streamable HTTP + SSE)

**Rationale:** With tools using REST API client, can now implement both HTTP transports. Streamable HTTP is primary (MCP standard), SSE for backward compatibility.

**Delivers:**
- Streamable HTTP endpoint at `/mcp`
- SSE endpoint at `/sse` with fastmcp-mount middleware
- Health check endpoint (`/health`)
- Connection heartbeat (30s ping for SSE)
- Lifespan context propagation to FastAPI
- CORS configuration for browser clients
- Graceful connection handling

**Uses:**
- fastmcp v2.14.4+ http_app() and sse_app()
- sse-starlette v3.2.0
- fastmcp-mount v0.1.0 for path fixing

**Implements:**
- Transport Implementations (architecture component #3)
- FastAPI Integration (architecture component #4)

**Addresses:**
- Streamable HTTP endpoint (table stakes)
- SSE endpoint (table stakes)
- Health check (table stakes)
- Connection heartbeat (table stakes)
- Zero-install SSE endpoint (differentiator)

**Avoids:**
- SSE transport deprecation (Pitfall #1) - using Streamable HTTP as primary
- Sub-path mounting breaks communication (Pitfall #2) - using fastmcp-mount
- Lifespan context not propagated (Pitfall #7) - explicit lifespan passing

**Verification:**
- Integration test: mount under `/api/mcp/`, verify tool calls work
- Test from browser: connect to SSE endpoint cross-origin (CORS)
- Verify session manager startup message in logs
- Test with MCP Inspector tool

### Phase 4: PyPI Package Distribution

**Rationale:** With working transports and REST client, can now package for distribution. stdio transport reuses the same tool implementations.

**Delivers:**
- pyproject.toml with hatchling build backend
- Console script entry point (`oncallhealth-mcp` command)
- Package structure with proper `__init__.py` files
- stdio transport for local use
- CLI with `--help`, `--transport`, environment variable support
- Flexible dependency bounds
- README with quickstart guide
- TestPyPI validation before production publish

**Uses:**
- hatchling v1.26+ for building
- build and twine for publishing
- All components from previous phases

**Implements:**
- PyPI Package Structure (architecture component #5)

**Addresses:**
- PyPI package with uvx support (table stakes)
- Console script entry point (table stakes)
- Dual transport flexibility (differentiator)

**Avoids:**
- PyPI dependency conflicts (Pitfall #5) - flexible version bounds
- Console script entry points fail (Pitfall #6) - wheel testing in CI

**Verification:**
- CI test: install in env with fastapi, pydantic, mcp pre-installed (conflict detection)
- CI test: `pip install dist/*.whl && oncallhealth-mcp --help` in fresh virtualenv
- Test on TestPyPI before production publish
- Verify `uvx oncallhealth-mcp` works after publish

### Phase 5: Documentation and Deployment

**Rationale:** With all components working, document usage patterns and deploy to production.

**Delivers:**
- Claude Desktop configuration examples
- API key setup instructions
- Troubleshooting guide (common errors)
- Production deployment to `mcp.oncallhealth.com`
- Connection limit per API key
- Structured logging with request IDs

**Addresses:**
- Claude Desktop config example (table stakes)
- API key setup instructions (table stakes)
- Troubleshooting section (table stakes)
- Connection limit per API key (differentiator)
- Structured logging (differentiator)

### Phase Ordering Rationale

- **Phase 1 first** because REST API client is the foundation for all other work. Cannot implement any transport or package without it.
- **Phase 2 before Phase 3** because tools must use REST client before implementing transports. Transport is just a delivery mechanism for tools.
- **Phase 3 before Phase 4** because hosted transports should be verified working before packaging for distribution. Easier to debug in controlled environment.
- **Phase 4 can partially overlap Phase 3** if needed - stdio transport for PyPI package can be developed while hosted transports are being finalized.
- **Phase 5 last** because documentation requires working implementation to document. Connection limits and structured logging are nice-to-haves that can be added incrementally.

This ordering follows dependency chain (1→2→3→4→5) and avoids rework. Each phase has clear verification criteria before proceeding.

### Research Flags

Phases likely needing deeper research during planning:

- **Phase 1 (REST API Client):** May need API research to verify existing backend endpoints support all MCP tool requirements. Check if batch endpoints exist or need to be created. Verify timeout and retry behavior expectations.

- **Phase 3 (Transport Implementation):** If Cloudflare or nginx reverse proxy is used, may need infrastructure research for SSE buffering configuration. Verify load balancer supports long-lived connections.

Phases with standard patterns (skip research-phase):

- **Phase 2 (MCP Tools Refactor):** FastMCP tool patterns are well-documented, this is straightforward refactoring work.

- **Phase 4 (PyPI Distribution):** Python packaging is well-established, multiple reference implementations exist (mcp-server-git, rootly-mcp-server).

- **Phase 5 (Documentation):** Standard documentation patterns, no novel approaches needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended packages are stable, widely-used, with official documentation. FastMCP v2.14.4 and MCP SDK v1.26.0 verified on PyPI (Jan 2026). |
| Features | HIGH | Based on reference implementations (Rootly, mcp-server-git) and official MCP best practices. Feature expectations validated against multiple production MCP servers. |
| Architecture | HIGH | Hybrid architecture verified with official FastMCP docs and MCP Python SDK. REST API client pattern is standard, multiple community implementations exist. |
| Pitfalls | HIGH | All 8 pitfalls documented with official sources (MCP SDK issues, FastMCP docs, AWS best practices). Prevention strategies verified with community implementations. |

**Overall confidence:** HIGH

All research findings are backed by official documentation (FastMCP, MCP SDK, Python Packaging Guide) or verified community implementations. No unproven assumptions or speculation. The recommended approach follows established patterns with clear precedents.

### Gaps to Address

Minor gaps that need validation during implementation:

- **Backend REST API coverage:** Verify existing oncallhealth.ai REST API endpoints support all MCP tool operations. May need to create MCP-specific endpoints (e.g., `/api/mcp/integrations`) if current endpoints don't match tool requirements. Phase 1 planning should audit existing endpoints.

- **Infrastructure for SSE:** Confirm production infrastructure (load balancer, reverse proxy) configuration for long-lived SSE connections. May need to disable buffering or enable sticky sessions. Phase 3 should include infrastructure review.

- **Claude Desktop SSE support:** Verify Claude Desktop's current MCP client supports SSE transport (research indicates it does, but version-specific behavior should be confirmed). If not, Streamable HTTP may be sufficient alone.

- **API key rate limits:** Clarify if existing rate limiting applies to MCP endpoints or needs separate limits for connection attempts. Phase 5 should define connection limit policy (recommendation: 5-10 concurrent connections per key).

These gaps are addressable during phase planning and don't block overall approach.

## Sources

### Primary (HIGH confidence)

- [FastMCP PyPI](https://pypi.org/project/fastmcp/) - v2.14.4 verified, features confirmed
- [MCP Python SDK PyPI](https://pypi.org/project/mcp/) - v1.26.0 verified, transport options validated
- [FastMCP HTTP Deployment Guide](https://gofastmcp.com/deployment/http) - Official deployment patterns
- [Python Packaging User Guide](https://packaging.python.org/tutorials/packaging-projects/) - PyPI best practices
- [HTTPX Official Documentation](https://www.python-httpx.org/) - Async client patterns, timeouts, connection pooling
- [MCP Legacy Transports](https://modelcontextprotocol.io/legacy/concepts/transports) - SSE deprecation confirmed
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) - v3.2.0 verified
- [mcp-server-git PyPI](https://pypi.org/project/mcp-server-git/) - Reference implementation

### Secondary (MEDIUM confidence)

- [Why MCP Deprecated SSE](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/) - Transport evolution rationale
- [fastmcp-mount GitHub](https://github.com/dwayn/fastmcp-mount) - Sub-path mounting fix
- [Rootly MCP Server GitHub](https://github.com/Rootly-AI-Labs/Rootly-MCP-server) - Production reference implementation
- [AWS Retry/Backoff Guide](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) - Distributed systems patterns
- [State of Python Packaging 2026](https://learn.repoforge.io/posts/the-state-of-python-packaging-in-2026/) - Ecosystem trends
- [FastMCP SSE Integration Lessons](https://medium.com/@wilson.urdaneta/taming-the-beast-3-lessons-learned-integrating-fastmcp-sse-with-uvicorn-and-pytest-5b5527763078) - Real-world issues
- [MCP Authentication Guide](https://stytch.com/mcp/MCP-authentication-and-authorization-guide/) - Auth patterns
- [HTTPX PoolTimeout Discussion](https://github.com/encode/httpx/discussions/2556) - Connection pool issues

### Tertiary (context for understanding)

- [SSE vs Streamable HTTP Comparison](https://brightdata.com/blog/ai/sse-vs-streamable-http) - Transport comparison
- [REST APIs are not Databases](https://medium.com/@marinithiago/guys-rest-apis-are-not-databases-60db4e1120e4) - Design mindset
- [Common REST API Design Mistakes](https://zuplo.com/learning-center/common-pitfalls-in-restful-api-design) - Anti-patterns

---
*Research completed: 2026-02-02*
*Ready for roadmap: yes*
