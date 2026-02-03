# Phase 5: REST API Client - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Build an HTTP client layer that the MCP server uses to call oncallhealth.ai REST APIs instead of direct database access. This client handles authentication (API key injection), resilience (retry, circuit breaker), error mapping, and connection pooling. This is the foundation for Phases 6-11.

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User has delegated all implementation decisions to Claude for this infrastructure layer. Key areas where Claude will make decisions during planning/research:

- **Error handling strategy**: Which HTTP errors trigger retry vs fail-fast, how to classify transient vs permanent failures
- **Retry configuration**: Number of retries, backoff timing (exponential with jitter), whether to make it configurable
- **Circuit breaker behavior**: When to open circuit, wait duration, half-open state handling
- **Timeout values**: Connect timeout vs read timeout, per-endpoint differences, sensible defaults
- **Connection pooling**: Pool size, keep-alive settings, connection limits
- **Request/response logging**: What to log, log levels, sanitization of sensitive data
- **Error mapping**: How HTTP status codes map to MCP exceptions

**Constraints from requirements:**
- Must use httpx (async client with connection pooling) - CLIENT-01
- Must implement exponential backoff retry (3-5 retries with jitter) - CLIENT-02
- Must implement circuit breaker to prevent retry storms - CLIENT-03
- Must have 5 second default timeout (configurable) - CLIENT-04
- Must map HTTP status codes to MCP exceptions - CLIENT-05
- Must monitor connection pool health and recreate if needed - CLIENT-06
- Must inject API key into all requests (X-API-Key header) - CLIENT-07
- Must support configurable base URL for oncallhealth.ai - CLIENT-08

**Research focus areas:**
- Best practices for httpx async client configuration
- Industry-standard retry/backoff patterns (e.g., AWS SDK patterns)
- Circuit breaker implementations (e.g., PyBreaker, custom)
- Error classification strategies (which 4xx/5xx errors are retriable)
- Connection pool health monitoring techniques

</decisions>

<specifics>
## Specific Ideas

No specific requirements — implementation should follow REST client best practices and the research findings from `.planning/research/v1.1-mcp-distribution/`.

**Key integration points:**
- Replace direct database queries in `backend/app/mcp/server.py` tools
- Call existing REST API endpoints at `/api/analysis/*` and `/api/integrations/*`
- Maintain API key authentication flow from v1.0

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-rest-api-client*
*Context gathered: 2026-02-02*
