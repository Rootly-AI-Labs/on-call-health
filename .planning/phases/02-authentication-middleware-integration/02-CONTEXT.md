# Phase 2: Authentication Middleware Integration - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend authentication to support both JWT (for OAuth web sessions) and API keys (for programmatic/MCP access). These serve different use cases and are not interchangeable:
- **Web users:** OAuth → JWT tokens (unchanged)
- **Programmatic users:** API keys (new capability)

This phase modifies backend authentication middleware only. API endpoint creation (Phase 3) and frontend UI (Phase 4) are separate.

</domain>

<decisions>
## Implementation Decisions

### Authentication Separation
- **MCP endpoints:** API keys ONLY - reject JWT entirely
- **Web endpoints:** JWT ONLY - reject API keys
- Clean separation by use case - no mixing of auth methods

### Error Responses
- **Specific error messages:** When API key fails, reveal why
  - "API key expired on 2026-02-15"
  - "API key has been revoked"
  - Not generic "Invalid credentials" - helpful for debugging
- Security tradeoff accepted: clarity over obscurity

### Rate Limiting
- **Global limit per key:** 100 req/min applies to all endpoints combined (not per-endpoint)
- **Same default for all keys:** No per-key configuration in v1 - all keys get same limit
- **Include Retry-After header:** When 429 returned, tell client when to retry
- Example: `HTTP 429 Too Many Requests` with `Retry-After: 45`

### Backward Compatibility
- **Greenfield:** No existing MCP users with JWT tokens - no migration needed
- **JWT tests must pass:** All existing JWT-based tests pass without modification
- **Web endpoints unchanged:** JWT-only web endpoints remain JWT-only

### Claude's Discretion
- **Auth precedence logic:** How to handle edge cases when both JWT and API key theoretically present
- **Per-key vs shared user limits:** Whether multiple keys share one user rate limit or each gets independent bucket
- **Auth dependency signature:** Whether to keep identical signature or add optional params - balance backward compatibility with clean implementation

</decisions>

<specifics>
## Specific Ideas

No specific requirements - open to standard approaches for authentication middleware patterns.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope

</deferred>

---

*Phase: 02-authentication-middleware-integration*
*Context gathered: 2026-01-30*
