# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** MCP clients and automation tools can authenticate reliably without JWT token expiration or session coupling.
**Current focus:** Phase 8 - API Key Authentication (MCP Integration)

## Current Position

Phase: 7 of 11 (Transport Implementation)
Plan: 2 of 2 in current phase
Status: Phase 7 complete
Last activity: 2026-02-03 - Completed 07-02-PLAN.md (FastAPI Mount)

Progress: [######----] 65% (v1.0 complete, Phase 5-7 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 14 (v1.0 + Phase 5 + Phase 6 + Phase 7)
- Average duration: ~7min (Phase 5-7)
- Total execution time: N/A

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1-4 (v1.0) | 8 | - | - |
| 5 (v1.1) | 2 | 17min | 8.5min |
| 6 (v1.1) | 2 | 9min | 4.5min |
| 7 (v1.1) | 2 | 23min | 11.5min |

**Recent Trend:**
- Last 5 plans: 06-01 (4min), 06-02 (5min), 07-01 (18min), 07-02 (5min)
- Trend: Phase 7 complete, ready for Phase 8 (API Key Auth + MCP)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- v1.0: Dual-hash pattern (SHA-256 + Argon2id) for fast validation
- v1.0: JWT-only for web, API-key-only for MCP (clean separation)
- v1.1: REST API Client must be foundation (research recommendation)
- v1.1: AWS deployment added as Phase 11 (ECS/Fargate, IaC)
- 05-01: httpx event hooks for API key injection (clean separation)
- 05-01: Lazy imports in mcp/__init__.py for client independence
- 05-02: Circuit breaker wraps retry function (counts request-level failures)
- 05-02: Retriable status codes (429, 5xx) trigger retry; 4xx fail fast
- 06-01: REST tool pattern: extract_api_key_header + async with OnCallHealthClient
- 06-01: Error mapping: NotFoundError -> LookupError for MCP contract compatibility
- 06-02: asyncio.gather with return_exceptions=True for parallel fetch with graceful failures
- 06-02: Support FastMCP 1.x sse_app() method in _resolve_asgi_app
- 07-01: Combined routes from FastMCP apps at top level (not Mount) for proper routing
- 07-01: Lifespan context manager initializes StreamableHTTPSessionManager
- 07-01: Health check at /health without auth for ALB compatibility
- 07-02: CORS applied at transport level to avoid FastMCP conflicts
- 07-02: SSE heartbeat documented for infrastructure-level config (Phase 9)
- 07-02: mcp-session-id exposed for browser session tracking

### Pending Todos

None.

### Blockers/Concerns

- Main app CORS middleware intercepts preflight before mounted app. May need X-API-Key in main app CORS if browser MCP clients require it.

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 07-02-PLAN.md (FastAPI Mount)
Resume file: None (ready for Phase 8)
