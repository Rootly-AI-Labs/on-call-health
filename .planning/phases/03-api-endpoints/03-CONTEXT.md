# Phase 3: API Endpoints - Context

**Gathered:** 2026-01-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Create REST API endpoints for API key CRUD operations (create, list, revoke). These endpoints are exclusively for the web UI and require JWT authentication. Programmatic API key management is deliberately excluded for security (prevents compromised key escalation).

</domain>

<decisions>
## Implementation Decisions

### Response structure
- Flat JSON for successful operations: `{"id": "123", "name": "Claude Desktop", ...}`
- List endpoint wrapped in object: `{"keys": [{...}, {...}]}` (allows adding pagination metadata later)
- Simple error format: `{"error": "Invalid API key name"}` (minimal)
- Standard REST status codes: 201 Created, 200 OK, 204 No Content for delete, 400 Bad Request, 404 Not Found

### Claude's Discretion
- Specific validation error messages (name format, expiration date rules)
- Rate limiting specifics (exact limits per endpoint)
- List endpoint sort order and filtering
- Audit logging level and format
- Handling duplicate key names
- Authorization failure error messages

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-api-endpoints*
*Context gathered: 2026-01-30*
