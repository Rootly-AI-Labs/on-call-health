# Phase 6: MCP Tools Refactor - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Migrate all MCP tools from direct database queries to REST API calls using OnCallHealthClient (built in Phase 5). This removes the database dependency from the MCP server, enabling distributed deployment via SSE/PyPI.

**In scope:**
- Replace SQLAlchemy queries with OnCallHealthClient REST calls
- Migrate analysis tools (start, status, results)
- Migrate integration tools (list)
- Remove database dependencies from MCP server module

**Out of scope:**
- New tool functionality or capabilities
- Changes to MCP protocol/contracts
- UI or user-facing behavior changes
- Creating new REST API endpoints (use existing oncallhealth.ai APIs)

</domain>

<decisions>
## Implementation Decisions

### Claude's Discretion

User has delegated ALL implementation decisions to Claude for this refactor. Key areas where Claude will make decisions during planning/research:

- **API endpoint mapping**: How MCP tools map to REST endpoints (one-to-one or custom mapping)
- **Error handling strategy**: How to surface REST errors as MCP exceptions (pass-through vs enhanced)
- **Data transformation**: Whether to transform API responses to match old schema or update tool contracts
- **Migration approach**: All-at-once vs phased migration, backward compatibility strategy
- **Testing strategy**: How to test refactored tools (mock REST client vs integration tests)
- **Client lifecycle**: Where to instantiate OnCallHealthClient (per-tool, shared singleton, context manager)
- **Response caching**: Whether to cache REST responses or call API on every tool invocation
- **Partial failure handling**: How tools behave when some API calls succeed and others fail

**Constraints from requirements:**
- Must use OnCallHealthClient from Phase 5 - TOOLS-01
- Must remove all direct database queries - TOOLS-05
- Must maintain existing tool functionality - TOOLS-01 through TOOLS-04
- Must handle REST errors appropriately - CLIENT-05 integration

**Research focus areas:**
- Existing REST API endpoints at `/api/analysis/*` and `/api/integrations/*`
- Current MCP tool implementations in `backend/app/mcp/server.py`
- Database schema vs API response format differences
- Error scenarios and how they're currently handled
- Existing test coverage patterns

</decisions>

<specifics>
## Specific Ideas

No specific requirements — implementation should follow best practices discovered in Phase 5 REST client research and existing MCP server patterns.

**Key integration points:**
- OnCallHealthClient is production-ready with retry, circuit breaker, and error mapping
- API endpoints exist at oncallhealth.ai for analysis and integrations
- MCP server uses API key authentication (same key for REST calls)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-mcp-tools-refactor*
*Context gathered: 2026-02-02*
