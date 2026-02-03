# Pitfalls Research

**Domain:** SSE-hosted MCP server with PyPI distribution
**Researched:** 2026-02-02
**Confidence:** HIGH (verified via official MCP SDK docs, FastMCP docs, and multiple community sources)

## Critical Pitfalls

### Pitfall 1: SSE Transport Deprecation - Building on Legacy Foundation

**What goes wrong:**
You invest significant effort implementing SSE transport, only to discover MCP deprecated SSE in specification version 2025-03-26 in favor of Streamable HTTP transport. Your implementation works but is now legacy.

**Why it happens:**
- SSE was the original remote transport for MCP
- Many tutorials and examples still reference SSE
- The deprecation happened relatively recently (March 2025)
- FastMCP still supports SSE for backward compatibility, masking the deprecation

**How to avoid:**
- Implement **Streamable HTTP as the primary transport**, SSE only for backward compatibility
- Use `transport="streamable-http"` with FastMCP, mount at `/mcp`
- Support both transports simultaneously during transition: `/mcp` for Streamable HTTP, `/sse` for legacy
- Follow official MCP SDK guidance: "Streamable HTTP transport is recommended for production deployments"

**Warning signs:**
- Documentation referring to "HTTP+SSE" or "dual endpoint" architecture
- Separate `/sse` and `/messages` endpoints instead of single `/mcp` endpoint
- Connection management complexity requiring session correlation between endpoints

**Phase to address:**
Phase 1 (Transport Implementation) - Choose Streamable HTTP from the start, add SSE as optional backward-compatibility layer.

**Sources:**
- [Why MCP Deprecated SSE](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/)
- [MCP Legacy Transports](https://modelcontextprotocol.io/legacy/concepts/transports)
- [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http)

---

### Pitfall 2: SSE Sub-path Mounting Breaks Client Communication

**What goes wrong:**
When mounting FastMCP's SSE transport under a sub-path in FastAPI (e.g., `/mcp/v1/`), the SSE `event: endpoint` message contains incorrect paths like `/messages/` instead of `/mcp/v1/messages/`. Clients receive 404 errors when posting messages back.

**Why it happens:**
- FastMCP generates the endpoint path without awareness of the ASGI mount path
- The `root_path` context is not automatically propagated to the SSE response stream
- This is a known architectural limitation in the official MCP SDK

**How to avoid:**
- Use the [`fastmcp-mount`](https://pypi.org/project/fastmcp-mount/) middleware to intercept and fix endpoint paths
- Or mount SSE app at the root path without sub-paths
- For Streamable HTTP: single endpoint avoids this issue entirely
- Test client communication immediately after mounting, not just SSE stream establishment

**Warning signs:**
- SSE connection establishes successfully but tool calls fail
- 404 errors on POST requests while GET `/sse` works
- Client logs showing wrong endpoint path in messages

**Phase to address:**
Phase 1 (Transport Implementation) - Verify path handling in integration tests before declaring transport complete.

**Sources:**
- [fastmcp-mount documentation](https://github.com/dwayn/fastmcp-mount)
- [Lessons Learned with FastMCP SSE](https://medium.com/@wilson.urdaneta/taming-the-beast-3-lessons-learned-integrating-fastmcp-sse-with-uvicorn-and-pytest-5b5527763078)

---

### Pitfall 3: Connection Pool Exhaustion and PoolTimeout in Long-Running HTTP Clients

**What goes wrong:**
After 3-12 hours of operation, the REST API client starts throwing `httpx.PoolTimeout` errors constantly. All requests fail immediately despite the backend being healthy. The issue requires service restart to resolve.

**Why it happens:**
- Long-lived `httpx.AsyncClient` instances can exhaust connection pools under certain failure patterns
- Connections may enter stuck states after network blips or backend restarts
- Default pool limits (100 connections, 20 keepalive) may be insufficient or misconfigured
- Race conditions in connection reuse after partial failures

**How to avoid:**
- Implement client health monitoring: if multiple consecutive PoolTimeouts occur, recreate the client
- Configure explicit limits: `httpx.Limits(max_connections=100, max_keepalive_connections=20, keepalive_expiry=30.0)`
- Add circuit breaker pattern: after N failures, stop retrying and fail fast
- Consider periodic client refresh (e.g., recreate client every 4 hours) as defensive measure
- Use connection pooling metrics/logging to detect degradation before total failure

**Warning signs:**
- Increasing latency on API calls before outright failure
- PoolTimeout errors appearing after extended uptime (hours, not minutes)
- Backend logs showing connections accepted but client reports timeout

**Phase to address:**
Phase 2 (REST API Client) - Implement robust client lifecycle management with health checks.

**Sources:**
- [HTTPX PoolTimeout Discussion](https://github.com/encode/httpx/discussions/2556)
- [HTTPX Resource Limits](https://www.python-httpx.org/advanced/resource-limits/)

---

### Pitfall 4: Retry Storm Amplification in Multi-Layer Architecture

**What goes wrong:**
When the backend REST API experiences transient failures, the MCP server retries. But multiple MCP clients are also retrying. The combined retry traffic is 243x normal load (3^5 for a 5-layer stack with 3 retries each), preventing the backend from ever recovering.

**Why it happens:**
- Each layer implements "reasonable" retry logic (3 retries with backoff)
- Retries multiply exponentially across layers: MCP client -> MCP server -> REST API -> backend services -> database
- No coordination between layers on retry budgets
- Jitter and backoff help but don't prevent amplification

**How to avoid:**
- **Implement retry budgets**: Only retry if total request time budget allows
- **Prefer retries at the edge**: Let the MCP client retry, not the MCP server
- **Add circuit breakers**: After N failures, stop retrying and return error immediately
- **Use deadline propagation**: Pass remaining time budget in request context
- **Rate limit retries**: Maximum N retries per second globally, not per request
- Respect `Retry-After` headers from rate-limited endpoints

**Warning signs:**
- Load on backend increases during outages instead of decreasing
- Recovery takes much longer than the original failure
- Log shows repeated retry sequences from multiple clients for same operation

**Phase to address:**
Phase 2 (REST API Client) - Design retry strategy with amplification in mind; implement circuit breaker.

**Sources:**
- [AWS: Timeouts, Retries, and Backoff with Jitter](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
- [HTTPX Retry Patterns](https://www.python-httpx.org/advanced/transports/)

---

### Pitfall 5: PyPI Dependency Conflicts with MCP SDK and FastAPI

**What goes wrong:**
Your package installs fine in isolation but causes dependency conflicts when users install it alongside other MCP servers or FastAPI applications. pip reports `ResolutionImpossible` or silently installs incompatible versions.

**Why it happens:**
- MCP SDK v1.x and v2.x have different dependency trees
- Pydantic v1 vs v2 conflicts are common in the FastAPI ecosystem
- Overly strict version pins (e.g., `fastapi==0.100.0`) conflict with user's existing installations
- Some packages still require `pydantic<2` while others require `pydantic>=2`

**How to avoid:**
- Use **flexible version bounds**: `fastapi>=0.100.0,<1.0.0` not `fastapi==0.100.0`
- Pin MCP SDK to stable v1.x branch: `mcp>=1.0.0,<2.0.0` (v2 is pre-alpha until Q1 2026)
- Test installation in realistic environments with common conflicting packages
- Use `pip-compile` or `poetry.lock` for development, but publish with flexible bounds
- Explicitly declare `pydantic>=2.0.0` if using Pydantic v2 features
- Run CI tests with both minimum and maximum supported dependency versions

**Warning signs:**
- "ResolutionImpossible" during pip install
- Runtime errors about missing attributes after successful install (version mismatch)
- Test suite passes locally but fails in CI with different dependency resolution

**Phase to address:**
Phase 3 (PyPI Distribution) - Define dependency bounds carefully; test installation matrix.

**Sources:**
- [Python Packaging: Dependency Resolution](https://pip.pypa.io/en/stable/topics/dependency-resolution/)
- [MCP Python SDK Version Guidance](https://github.com/modelcontextprotocol/python-sdk)
- [State of Python Packaging 2026](https://learn.repoforge.io/posts/the-state-of-python-packaging-in-2026/)

---

### Pitfall 6: Console Script Entry Points Not Working After PyPI Install

**What goes wrong:**
The `oncall-health-mcp` command works when installed locally with `pip install -e .` but fails or is missing after installing from PyPI. Users report "command not found" or import errors.

**Why it happens:**
- Entry point behavior differs between editable installs and wheel installs from PyPI
- Local installs with `setup.py develop` rely on setuptools runtime, PyPI wheels don't
- Missing `__init__.py` files in package structure break imports
- Entry point function references a module path that doesn't exist in the installed package

**How to avoid:**
- **Build wheels, not just source distributions**: `python -m build` generates both
- Test the actual wheel: `pip install dist/*.whl` in a fresh virtualenv
- Verify entry point module paths match actual package structure
- Use `importlib.metadata` to read version from package metadata instead of hardcoding
- Test on TestPyPI before publishing to production PyPI
- Include `py_modules` or `packages` explicitly in `pyproject.toml`

**Warning signs:**
- Entry point works with `python -m oncall_health_mcp` but not `oncall-health-mcp` command
- Different behavior between `pip install -e .` and `pip install .`
- Import errors mentioning paths that exist in source but not installed package

**Phase to address:**
Phase 3 (PyPI Distribution) - Build and test wheel installation in CI before every release.

**Sources:**
- [Setuptools Entry Points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html)
- [Python Packaging: Console Scripts](https://python-packaging.readthedocs.io/en/latest/command-line-scripts.html)
- [Different behavior local vs PyPI](https://github.com/pypa/pip/issues/1728)

---

### Pitfall 7: Lifespan Context Not Propagated to Mounted ASGI App

**What goes wrong:**
The MCP server mounts successfully into FastAPI, but session management fails silently. Connections are accepted but tools don't work, or state is lost between requests. No obvious error message.

**Why it happens:**
- FastMCP's session manager requires proper lifespan initialization
- When mounting MCP apps in Starlette/FastAPI, nested lifespans are not automatically recognized
- The parent app's lifespan runs, but the MCP app's lifespan is never called
- This is a subtle issue that doesn't cause immediate errors

**How to avoid:**
- **Pass the lifespan context explicitly** from FastMCP to the parent Starlette/FastAPI app
- For Streamable HTTP: `app = Starlette(lifespan=mcp.lifespan, routes=[Mount("/mcp", app=mcp.http_app())])`
- Test session state persistence across multiple requests, not just initial connection
- Add startup/shutdown logging in the MCP app to verify lifespan execution

**Warning signs:**
- First request works, subsequent requests fail
- "Session not found" errors
- Memory leaks (sessions never cleaned up)
- State reset between requests when it should persist

**Phase to address:**
Phase 1 (Transport Implementation) - Explicitly wire lifespan context in ASGI mounting.

**Sources:**
- [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http)
- [Running MCP Servers - DeepWiki](https://deepwiki.com/modelcontextprotocol/python-sdk/9.1-running-servers)

---

### Pitfall 8: Treating REST API Like Direct Database Access

**What goes wrong:**
Code migrated from direct DB access assumes synchronous, instant responses. The REST API client fetches data one item at a time in loops, issues N+1 query patterns over HTTP, and has no error handling for network failures.

**Why it happens:**
- Direct DB access (the current implementation) returns immediately
- Developers port code line-by-line without rethinking data access patterns
- ORM habits (eager loading, lazy relationships) don't translate to REST APIs
- "It worked with the database" mentality ignores network latency and failure modes

**How to avoid:**
- **Design API contracts before migrating**: What bulk endpoints are needed?
- **Batch requests**: Replace N individual fetches with one batch endpoint
- **Handle partial failures**: API might return some items, fail on others
- **Add timeouts everywhere**: No request should hang indefinitely
- **Cache aggressively**: API responses are slower than DB queries
- **Consider GraphQL patterns**: Request exactly the data needed, no over/under-fetching

**Warning signs:**
- Sequential HTTP requests in loops
- No error handling in API client code
- Missing timeouts on requests
- Latency 10-100x higher than direct DB version

**Phase to address:**
Phase 2 (REST API Client) - Design client with network-first mindset, not database-port mindset.

**Sources:**
- [REST APIs are not Databases](https://medium.com/@marinithiago/guys-rest-apis-are-not-databases-60db4e1120e4)
- [Common REST API Design Mistakes](https://zuplo.com/learning-center/common-pitfalls-in-restful-api-design)

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Direct DB queries in MCP server | Faster development, lower latency | Impossible to distribute, couples deployment | Never for SSE-hosted version |
| Hardcoded API base URL | Quick to implement | Breaks different environments | Only in development |
| Synchronous HTTP calls in async handlers | Simpler code | Blocks event loop, degrades concurrency | Never |
| Single global httpx client without refresh | Less code | PoolTimeout crashes after hours | Never in production |
| Skipping TestPyPI release | Faster publishing | Broken PyPI release discovered by users | Never for first release |
| Version pinning all dependencies | Reproducible builds | Conflicts with user environments | Only in lockfiles, not published requirements |
| SSE-only transport | Fewer code paths | Legacy protocol, poor scalability | Never as sole transport |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| FastAPI mount | Mounting MCP app without passing lifespan context | Pass `lifespan` from FastMCP to parent Starlette app |
| Nginx reverse proxy | Default response buffering delays SSE events | Add `X-Accel-Buffering: no` header |
| Cloudflare proxy | 100KB buffer accumulation before flush | Use Cloudflare Workers or disable buffering |
| Docker health checks | HTTP health check on SSE endpoint | Separate `/health` endpoint with quick response |
| Gunicorn workers | Using sync workers for async MCP server | Use `uvicorn.workers.UvicornWorker` for async support |
| Load balancer | Round-robin breaking SSE session affinity | Enable sticky sessions or use Streamable HTTP |
| CORS | Missing `Access-Control-Expose-Headers` | Expose `Mcp-Session-Id` header for browser clients |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Unbounded SSE connections | Memory exhaustion, file descriptor limits | Use `ConnectionLimiter` (default 100), implement backpressure | ~1000 concurrent connections |
| No pagination in list endpoints | Timeout on `integrations_list` | Paginate all list operations in REST API | ~100 integrations per user |
| Synchronous Argon2 verification | Event loop blocking, high latency | Use `asyncio.to_thread()` for CPU-bound crypto | ~10 concurrent auth requests |
| Creating new DB session per request | Connection pool exhaustion | Use dependency injection with session lifecycle | ~50 concurrent requests |
| Missing connection timeout | Hung requests consuming workers | Set explicit connect/read/write timeouts | Any network instability |
| HTTP/1.1 with many SSE clients | Browser 6-connection limit per origin | Use HTTP/2 for multiplexing | ~6 concurrent browser connections |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Passing user's API key to downstream APIs | Confused deputy attack - downstream trusts unintended token | MCP spec prohibits token passthrough; use server's own credentials for downstream |
| Missing CORS on SSE endpoint | Browser-based clients blocked | Configure `Access-Control-Allow-Origin`, `Access-Control-Expose-Headers: Mcp-Session-Id` |
| Logging API keys in error messages | Credential exposure in logs | Scrub `Authorization` and `X-API-Key` headers before logging |
| No rate limiting on SSE connections | DoS via connection exhaustion | Limit connections per API key, implement connection throttling |
| Hardcoded API keys in published package | Credentials on PyPI forever | Use environment variables, fail fast if not configured |
| JWT/API key dual acceptance on same endpoint | Token confusion, auth bypass | MCP endpoints should be API-key-only (current implementation is correct) |
| No session token validation | Session hijacking | Validate `Mcp-Session-Id` belongs to authenticated user |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **SSE Transport:** Often missing error handling for client disconnect mid-stream - verify `GeneratorExit` handling
- [ ] **REST API Client:** Often missing timeout configuration - verify all four timeout types (connect, read, write, pool)
- [ ] **PyPI Package:** Often missing `py.typed` marker - verify package works with mypy/pyright in strict mode
- [ ] **Entry Points:** Often missing in wheel builds - verify command works after `pip install dist/*.whl`
- [ ] **Streamable HTTP:** Often missing lifespan context propagation - verify session manager initializes correctly
- [ ] **Rate Limiting:** Often per-endpoint only - verify limits apply across SSE connection establishment too
- [ ] **Health Endpoint:** Often checks SSE availability - verify it returns quickly without establishing SSE connection
- [ ] **CORS:** Often missing `Access-Control-Expose-Headers` - verify browser clients can read `Mcp-Session-Id`
- [ ] **Retry Logic:** Often retries on all errors - verify it does NOT retry on 4xx client errors

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| SSE path mounting breaks clients | LOW | Add fastmcp-mount middleware, redeploy |
| Connection pool exhaustion | LOW | Implement client recreation logic, deploy hotfix |
| Retry storm | MEDIUM | Add circuit breaker, may need coordinated deploy across services |
| PyPI dependency conflicts | MEDIUM | Release new version with relaxed bounds, users reinstall |
| Entry point not working | MEDIUM | Fix pyproject.toml, release new version, users reinstall |
| Hardcoded credentials published | HIGH | Rotate ALL credentials immediately, yank PyPI version, audit access logs |
| Built on deprecated SSE only | HIGH | Add Streamable HTTP support, deprecate SSE endpoints, coordinate client migration |
| Lifespan context missing | LOW | Update mounting code, redeploy; may need to restart client connections |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| SSE deprecation (use Streamable HTTP) | Phase 1: Transport | Streamable HTTP endpoint responds at `/mcp` |
| Sub-path mounting breaks paths | Phase 1: Transport | Integration test: mount under `/api/mcp/`, verify tool calls work |
| Lifespan context not propagated | Phase 1: Transport | Verify session manager startup message in logs |
| Connection pool exhaustion | Phase 2: API Client | Stress test: run 12+ hours with simulated network failures |
| Retry storm amplification | Phase 2: API Client | Load test: simulate backend failure, verify load doesn't amplify |
| REST API as database anti-pattern | Phase 2: API Client | Code review: no sequential HTTP in loops, all requests have timeouts |
| Dependency conflicts | Phase 3: PyPI | CI test: install in env with fastapi, pydantic, mcp pre-installed |
| Entry point failures | Phase 3: PyPI | CI test: `pip install dist/*.whl && oncall-health-mcp --help` in fresh env |
| CORS blocking browser clients | Phase 1: Transport | Test from browser: connect to SSE endpoint cross-origin |
| Rate limiting gaps | Phase 2: API Client | Test: exceed rate limit on SSE connect, verify rejection |

---

## Sources

**Official Documentation:**
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) - Version guidance, transport options
- [FastMCP HTTP Deployment](https://gofastmcp.com/deployment/http) - Mounting, configuration
- [Python Packaging User Guide](https://packaging.python.org/guides/distributing-packages-using-setuptools/) - PyPI best practices
- [HTTPX Documentation](https://www.python-httpx.org/advanced/) - Timeouts, connection pooling, retries

**Security & Authentication:**
- [MCP Authentication Guide](https://mcp-framework.com/docs/Authentication/overview/) - Auth patterns
- [MCP Authorization Spec](https://modelcontextprotocol.io/docs/tutorials/security/authorization) - Security model
- [CORS for MCP Servers](https://mcpcat.io/guides/implementing-cors-policies-web-based-mcp-servers/) - Browser security

**Community Wisdom:**
- [Why MCP Deprecated SSE](https://blog.fka.dev/blog/2025-06-06-why-mcp-deprecated-sse-and-go-with-streamable-http/) - Transport evolution
- [AWS Retry/Backoff Guide](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/) - Distributed systems patterns
- [FastMCP SSE Integration Lessons](https://medium.com/@wilson.urdaneta/taming-the-beast-3-lessons-learned-integrating-fastmcp-sse-with-uvicorn-and-pytest-5b5527763078) - Real-world issues
- [fastmcp-mount](https://github.com/dwayn/fastmcp-mount) - Sub-path mounting fix

**PyPI & Packaging:**
- [Setuptools Entry Points](https://setuptools.pypa.io/en/latest/userguide/entry_point.html) - Console scripts
- [pip Dependency Resolution](https://pip.pypa.io/en/stable/topics/dependency-resolution/) - Conflict resolution
- [State of Python Packaging 2026](https://learn.repoforge.io/posts/the-state-of-python-packaging-in-2026/) - Current ecosystem

**REST API Design:**
- [REST APIs are not Databases](https://medium.com/@marinithiago/guys-rest-apis-are-not-databases-60db4e1120e4) - Design mindset
- [Common REST API Mistakes](https://zuplo.com/learning-center/common-pitfalls-in-restful-api-design) - Anti-patterns

---
*Pitfalls research for: SSE-hosted MCP server with PyPI distribution*
*Researched: 2026-02-02*
