---
phase: 09-infrastructure
plan: 02
subsystem: infra
tags: [apscheduler, logging, cleanup, asyncio, mcp]

# Dependency graph
requires:
  - phase: 09-01
    provides: Connection tracker, rate limiter, middleware
provides:
  - Periodic cleanup task for stale MCP connections
  - Structured logging for MCP infrastructure events
  - APScheduler integration for cleanup job
affects: [10-security-hardening, 11-aws-deployment]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Structured logging with event types and automatic level selection
    - APScheduler job config factory pattern

key-files:
  created:
    - backend/app/mcp/infrastructure/logging.py
    - backend/app/mcp/infrastructure/cleanup.py
  modified:
    - backend/app/mcp/infrastructure/middleware.py
    - backend/app/mcp/infrastructure/__init__.py
    - backend/app/main.py

key-decisions:
  - "STALE_CONNECTION_TIMEOUT_MINUTES=10 (2x cleanup interval for safety)"
  - "Separate AsyncIOScheduler for MCP cleanup (independent of survey scheduler)"
  - "DEBUG for normal ops, WARN for violations, ERROR for failures"

patterns-established:
  - "MCPEvent constants for event type standardization"
  - "log_mcp_event with automatic level selection based on event type"
  - "get_cleanup_job_config factory for APScheduler job registration"

# Metrics
duration: 5min
completed: 2026-02-03
---

# Phase 9 Plan 02: Graceful Cleanup and Structured Logging Summary

**APScheduler cleanup task (every 5 min, 10 min staleness threshold) with structured logging (DEBUG for connections, WARN for limits)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-02-03T15:07:24Z
- **Completed:** 2026-02-03T15:12:16Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Created structured logging module with MCPEvent constants and automatic log level selection
- Implemented periodic cleanup task that removes stale connections every 5 minutes
- Integrated logging into middleware for all connection lifecycle and limit violation events
- Registered MCP cleanup scheduler in main.py startup

## Task Commits

Each task was committed atomically:

1. **Task 1: Create structured logging module** - `284704cc` (feat)
2. **Task 2: Create cleanup task module** - `d5e1db9e` (feat)
3. **Task 3: Integrate logging and cleanup** - `39461e50` (feat)

## Files Created/Modified

- `backend/app/mcp/infrastructure/logging.py` - Structured MCP event logging with MCPEvent constants
- `backend/app/mcp/infrastructure/cleanup.py` - Periodic cleanup task for stale connections
- `backend/app/mcp/infrastructure/middleware.py` - Added logging calls for all events
- `backend/app/mcp/infrastructure/__init__.py` - Export all logging and cleanup functions
- `backend/app/main.py` - Register MCP cleanup scheduler on startup

## Decisions Made

- **STALE_CONNECTION_TIMEOUT_MINUTES=10:** Set to 2x the cleanup interval (5 min) for safety margin, as recommended in research
- **Separate scheduler:** Using independent AsyncIOScheduler for MCP cleanup rather than reusing survey scheduler for clarity and independence
- **Log levels:** DEBUG for connection_open/close/cleanup_completed, WARNING for connection_limit_hit/rate_limit_hit, ERROR for cleanup_failed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 9 (Infrastructure) complete
- Connection tracking, rate limiting, cleanup, and logging all in place
- Ready for Phase 10 (Security Hardening)

---
*Phase: 09-infrastructure*
*Completed: 2026-02-03*
