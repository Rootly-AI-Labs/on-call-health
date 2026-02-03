# Phase 9: Infrastructure - Context

**Gathered:** 2026-02-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Add production infrastructure safeguards to the hosted MCP endpoint to protect against resource exhaustion and abuse. This ensures the hosted endpoint at `/mcp/*` can handle multiple users without any single user or API key monopolizing server resources.

**In scope:**
- Connection limits per API key (max concurrent connections)
- Rate limiting for MCP tool invocations (requests per minute)
- Graceful cleanup of disconnected clients
- Connection event logging for debugging and monitoring
- Middleware/decorator pattern for applying limits

**Out of scope:**
- Metrics and monitoring dashboards (deferred to post-v1.1)
- Authentication changes (API key auth exists from Phase 4)
- MCP tool modifications (tools are stable from Phase 6)
- Performance optimization beyond limits (future work)
- Auto-scaling configuration (Phase 11 - AWS Deployment)

</domain>

<decisions>
## Implementation Decisions

### Connection Limit Strategy

**Maximum concurrent connections per API key: Claude's discretion**
- User delegated to Claude: Choose reasonable limit based on resource capacity
- Research should consider: Typical MCP client usage (1-3 Claude Desktop windows), server capacity, memory per connection

**Limit behavior: Reject new connections with 429 error**
- User decision: Clear error message when limit reached
- Client must close existing connections before opening new ones
- Error response should include retry guidance (e.g., "Close idle connections and retry")

**Limit granularity: Same limit for all transports**
- User decision: Simplicity over complexity
- SSE and Streamable HTTP share the same connection pool per API key
- No separate tracking per transport type

**Additional constraints:**
- Must track connections per API key (not per user, not globally)
- Must handle connection cleanup properly (decrement count on disconnect)
- Must be thread-safe (multiple concurrent connection attempts)

### Rate Limiting Approach

**Rate limit strategy: Requests per minute**
- User decision: Simple time-window approach
- Implementation: Fixed window or sliding window (Claude's discretion)
- Easier to understand and explain to users than token bucket

**Rate limit independence: Separate MCP rate limits**
- User decision: MCP endpoint has its own limits independent of `/api/*` endpoints
- Prevents MCP from exhausting main API quota
- Allows different limits for interactive (MCP) vs programmatic (API) usage

**Per-tool limits: Higher limits for expensive tools**
- User decision: Different tools get different rate limits
- Example logic: analysis_start (expensive, lower limit) vs analysis_status (cheap, higher limit)
- Claude will determine specific limits based on tool resource usage

**Additional constraints:**
- Rate limits per API key (not global across all users)
- Must return 429 with Retry-After header on limit hit
- Must NOT rate limit health check endpoint `/health` (ALB needs it)

### Cleanup and Lifecycle

**Disconnect detection: Claude's discretion**
- User delegated to Claude: Choose between heartbeat timeout vs connection close events
- Consider transport characteristics (SSE keeps alive differently than HTTP)
- Must handle both graceful disconnect and connection drops

**Cleanup frequency: Every 5 minutes**
- User decision: Background task runs every 5 minutes
- Reasonable balance between cleanup speed and CPU overhead
- Stale connections cleaned up within 5 minutes

**Cleanup style: Graceful (send close message first)**
- User decision: Notify client before cleaning up server resources
- Better user experience (client knows why connection closed)
- Then release server resources (memory, connection slots, rate limit state)

**Additional constraints:**
- Must prevent resource leaks (connections, memory, file handles)
- Must decrement connection count when cleanup happens
- Must handle cleanup failures gracefully (log but don't crash)

### Logging and Observability

**Events to log: Connection open/close, rate limit hits, connection limit rejections**
- User decision: Log infrastructure events, not every MCP request
- Connection lifecycle: When clients connect and disconnect
- Limit violations: When rate limits or connection limits are hit
- NOT logging: Individual tool invocations (too verbose)

**Log levels: DEBUG for connections, WARN for limits**
- User decision: Normal operations quiet, violations visible
- DEBUG: Connection open, connection close (quiet in production)
- WARN: Rate limit hit, connection limit rejection (visible)
- ERROR: Cleanup failures, unexpected errors

**Metrics: No, logs only for now**
- User decision: Keep it simple - structured logs only
- Deferred: Prometheus/CloudWatch metrics can be added later if needed
- Logs should be structured (JSON) for easy parsing

**Log format:**
- Must include: timestamp, API key (hashed/truncated), event type, connection details
- Example: `{"timestamp": "...", "api_key": "och_***xyz", "event": "connection_open", "transport": "http"}`

### Claude's Discretion (Additional Areas)

User has delegated these decisions to Claude during planning/research:

- **Specific connection limit value**: 5, 10, or other based on capacity
- **Specific rate limit values**: Requests per minute per tool
- **Rate limit implementation**: Fixed window vs sliding window
- **Disconnect detection method**: Heartbeat timeout vs connection events
- **Middleware architecture**: Where to inject limits (FastAPI middleware, decorator, transport layer)
- **State storage**: In-memory (simple) vs Redis (distributed) for connection/rate tracking
- **Connection tracking data structure**: Dict, set, or database table
- **Retry-After header calculation**: How to tell clients when to retry
- **Error message content**: Exact wording for 429 responses

**Constraints from requirements:**
- Single user cannot exhaust resources (max 5-10 concurrent connections) - INFRA-01
- Single API key cannot exhaust connections (per-key limits) - INFRA-02
- MCP endpoint has rate limiting independent of API endpoints - INFRA-03
- Disconnected clients cleaned up gracefully (no resource leaks) - INFRA-04
- Connection events logged for debugging - INFRA-05

**Research focus areas:**
- FastAPI middleware patterns for rate limiting and connection tracking
- Existing rate limiting libraries (slowapi, fastapi-limiter, custom)
- State management approaches (in-memory vs Redis for distributed deployment)
- MCP protocol conventions for connection lifecycle
- HTTP 429 response format with Retry-After header
- Structured logging patterns for FastAPI applications
- Connection tracking in async Python (asyncio, threading concerns)

</decisions>

<specifics>
## Specific Ideas

**User preferences captured:**
- Reject new connections with 429 when limit hit (don't rotate)
- Same limit for all transports (simple)
- Requests per minute rate limiting (not token bucket)
- Separate MCP rate limits (independent from main API)
- Higher limits for expensive tools (analysis_start has lower limit)
- Cleanup every 5 minutes (background task)
- Graceful cleanup (notify client first)
- Log connections at DEBUG, limits at WARN
- No metrics for now (logs only)

**Integration points:**
- Phase 7: Transport layer at `/mcp/*` endpoints (where limits apply)
- Phase 4: API key authentication (used for per-key tracking)
- Existing FastAPI middleware stack in main.py
- Existing logging configuration

**Deferred to future:**
- Metrics and monitoring dashboards
- Auto-scaling based on connection count
- Dynamic rate limit adjustment
- Per-user quotas (currently per-API-key)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 09-infrastructure*
*Context gathered: 2026-02-03*
