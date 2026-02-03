# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-02)

**Core value:** MCP clients and automation tools can authenticate reliably without JWT token expiration or session coupling.
**Current focus:** Phase 9 - Infrastructure (Complete)

## Current Position

Phase: 9 of 11 (Infrastructure)
Plan: 2 of 2 in current phase
Status: Phase complete
Last activity: 2026-02-03 - Completed 09-02-PLAN.md (Graceful Cleanup and Structured Logging)

Progress: [########--] 82% (v1.0 complete, Phase 5-9 complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 18 (v1.0 + Phase 5 + Phase 6 + Phase 7 + Phase 8 + Phase 9)
- Average duration: ~7min (Phase 5-9)
- Total execution time: N/A

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1-4 (v1.0) | 8 | - | - |
| 5 (v1.1) | 2 | 17min | 8.5min |
| 6 (v1.1) | 2 | 9min | 4.5min |
| 7 (v1.1) | 2 | 23min | 11.5min |
| 8 (v1.1) | 2 | 13min | 6.5min |
| 9 (v1.1) | 2 | 14min | 7min |

**Recent Trend:**
- Last 5 plans: 08-01 (8min), 08-02 (5min), 09-01 (9min), 09-02 (5min)
- Trend: Phase 9 complete, infrastructure safeguards fully operational

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
- 08-01: Package name oncallhealth-mcp with hatchling build backend
- 08-01: CLI validates ONCALLHEALTH_API_KEY before starting
- 08-01: Flexible dependency bounds (>=X.Y,<Z.0) for PyPI compatibility
- 08-02: Lazy import of server module for validation-first CLI startup
- 08-02: README structure: install -> quick start -> config -> CLI -> integration -> tools
- 09-01: MAX_CONNECTIONS_PER_KEY=5 (conservative for typical MCP usage)
- 09-01: Per-tool rate limits (5/min expensive, 60/min cheap, 100/min default)
- 09-01: Infrastructure middleware before CORS (reject early)
- 09-02: STALE_CONNECTION_TIMEOUT_MINUTES=10 (2x cleanup interval for safety)
- 09-02: Separate AsyncIOScheduler for MCP cleanup (independent of survey scheduler)
- 09-02: Log levels: DEBUG for normal ops, WARN for violations, ERROR for failures

### Pending Todos

None.

### Blockers/Concerns

- Main app CORS middleware intercepts preflight before mounted app. May need X-API-Key in main app CORS if browser MCP clients require it.

## Session Continuity

Last session: 2026-02-03
Stopped at: Completed 09-02-PLAN.md (Graceful Cleanup and Structured Logging)
Resume file: None (Phase 9 complete, ready for Phase 10)
