---
phase: 09-infrastructure
plan: 01
subsystem: mcp-infrastructure
tags: [rate-limiting, connection-tracking, middleware, starlette]

dependency_graph:
  requires:
    - "07-01: MCP transport layer at /mcp/*"
    - "04-*: API key authentication infrastructure"
  provides:
    - "Connection tracking per API key (max 5 concurrent)"
    - "Per-tool rate limiting for MCP endpoints"
    - "MCPInfrastructureMiddleware for Starlette"
  affects:
    - "09-02: Cleanup tasks (uses connection_tracker.get_stale_connections)"
    - "11-*: AWS deployment (middleware works with load balancer)"

tech_stack:
  added: []
  patterns:
    - "asyncio.Lock for thread-safe connection state"
    - "Starlette BaseHTTPMiddleware for infrastructure checks"
    - "SlowAPI storage for rate limit state"

file_tracking:
  created:
    - backend/app/mcp/infrastructure/__init__.py
    - backend/app/mcp/infrastructure/connection_tracker.py
    - backend/app/mcp/infrastructure/rate_limiter.py
    - backend/app/mcp/infrastructure/middleware.py
  modified:
    - backend/app/mcp/transport.py

decisions:
  - context: "Connection limit value"
    choice: "MAX_CONNECTIONS_PER_KEY = 5"
    rationale: "Conservative limit allows 3-4 Claude Desktop windows + buffer"
  - context: "Rate limit per-tool values"
    choice: "5/min expensive, 60/min cheap, 100/min default"
    rationale: "Based on resource consumption analysis from research"
  - context: "Middleware position in stack"
    choice: "Infrastructure before CORS"
    rationale: "Reject over-limit requests before CORS processing overhead"

metrics:
  duration: "9 minutes"
  completed: "2026-02-03"
---

# Phase 09 Plan 01: Connection Tracking and Rate Limiting Summary

**One-liner:** In-memory connection tracking with asyncio.Lock and per-tool rate limiting via SlowAPI integration, applied through Starlette middleware.

## What Was Built

Created the MCP infrastructure safeguards module to protect against resource exhaustion:

1. **Connection Tracker** (`connection_tracker.py`)
   - `ConnectionState` dataclass with thread-safe `asyncio.Lock`
   - Tracks connections per API key ID with `defaultdict(set)`
   - `add_connection()` with atomic check-and-add (prevents race conditions)
   - `remove_connection()` with empty set cleanup (prevents memory growth)
   - `get_stale_connections()` for cleanup task support (Phase 9-02)
   - Module singleton: `connection_tracker = ConnectionState()`

2. **Rate Limiter** (`rate_limiter.py`)
   - `MCP_RATE_LIMITS` dict with per-tool limits:
     - `analysis_start`: 5/minute (expensive: creates background job)
     - `integrations_list`: 20/minute (expensive: parallel fetches)
     - `analysis_status`: 60/minute (cheap: single DB query)
     - `analysis_results`: 60/minute (cheap: single DB query)
     - `analysis_current`: 30/minute (cheap: list query)
     - `default`: 100/minute (fallback)
   - `extract_tool_name()` parses MCP tools/call request body
   - `check_rate_limit()` returns 429 JSONResponse with Retry-After header

3. **Infrastructure Middleware** (`middleware.py`)
   - `MCPInfrastructureMiddleware(BaseHTTPMiddleware)`
   - Health check bypass: `/health` always passes through
   - Connection limit check before processing request
   - Rate limit check for tool calls
   - try/finally ensures connection cleanup on all paths
   - Reuses `compute_sha256_hash` for API key lookup

4. **Transport Integration** (`transport.py`)
   - Added `infrastructure_middleware` to middleware stack
   - Position: before CORS (infrastructure checks run first)

## Key Implementation Details

### Thread Safety Pattern
```python
async def add_connection(self, api_key_id: int, connection_id: str) -> bool:
    async with self._lock:
        if len(self.connections[api_key_id]) >= MAX_CONNECTIONS_PER_KEY:
            return False
        self.connections[api_key_id].add(connection_id)
        self.last_activity[connection_id] = datetime.now(timezone.utc)
        return True
```

### 429 Response Format
```python
JSONResponse(
    status_code=429,
    content={
        "error": "connection_limit_exceeded",
        "detail": "Maximum concurrent connections reached (5). Close idle connections and retry.",
        "retry_after": 60,
    },
    headers={"Retry-After": "60"},
)
```

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Connection limit | 5 per API key | Conservative for typical MCP usage (3-4 Claude windows) |
| State storage | In-memory | Matches single-server deployment; Redis migration path available |
| Rate limit storage | SlowAPI (existing) | Reuses existing infrastructure with Redis fallback |
| Middleware position | Before CORS | Reject early to avoid CORS processing overhead |

## Deviations from Plan

**[Rule 3 - Blocking] Fixed SessionLocal import path**
- **Found during:** Task 3
- **Issue:** Plan specified `from app.database import SessionLocal` but correct path is `from app.models import SessionLocal`
- **Fix:** Changed import to match existing codebase pattern
- **Files modified:** backend/app/mcp/infrastructure/middleware.py
- **Commit:** af7a1c55

## Verification Results

All success criteria met:
- [x] backend/app/mcp/infrastructure/ module exists
- [x] MAX_CONNECTIONS_PER_KEY = 5
- [x] MCP_RATE_LIMITS has analysis_start at 5/min, analysis_status at 60/min
- [x] MCPInfrastructureMiddleware integrated into mcp_http_app middleware stack
- [x] Health check endpoint explicitly bypassed
- [x] 429 responses include Retry-After header and structured error JSON
- [x] All files compile without syntax errors

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 9e54865d | feat | Add connection tracker module for MCP infrastructure |
| c9de1449 | feat | Add MCP rate limiter with per-tool limits |
| af7a1c55 | feat | Add infrastructure middleware and integrate with transport |

## Next Phase Readiness

**Ready for 09-02:** Cleanup tasks
- `connection_tracker.get_stale_connections(cutoff)` method available
- Cleanup task can iterate stale connections and call `remove_connection()`
- APScheduler pattern available from existing survey_scheduler.py

**Dependencies resolved:**
- Connection state tracking: Complete
- Rate limit infrastructure: Complete
- Middleware integration: Complete
