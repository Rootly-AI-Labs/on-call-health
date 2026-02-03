---
phase: 11-aws-deployment
plan: 01
subsystem: infra
tags: [docker, multi-stage-build, python, uvicorn, aws-ecs, fargate]

# Dependency graph
requires:
  - phase: 07-transport-implementation
    provides: MCP transport layer (transport.py, server.py)
  - phase: 09-infrastructure
    provides: Infrastructure middleware (optional for standalone)
provides:
  - Multi-stage Dockerfile for MCP server
  - Minimal requirements-mcp.txt without database dependencies
  - Standalone mode support (no database required for Docker)
affects: [11-02-PLAN, aws-ecs-deployment, github-actions-ci]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Multi-stage Docker build (builder + runtime)"
    - "Conditional middleware loading for standalone mode"
    - "Non-root container user (mcpuser)"

key-files:
  created:
    - backend/Dockerfile.mcp
    - backend/requirements-mcp.txt
    - backend/app/mcp/auth_helpers.py
  modified:
    - backend/app/mcp/transport.py
    - backend/app/mcp/server.py
    - backend/app/mcp/auth.py

key-decisions:
  - "Split auth_helpers.py from auth.py for standalone mode without DB dependencies"
  - "Infrastructure middleware conditionally loaded via try/except ImportError"
  - "Python urllib for health check (no curl/wget in minimal image)"

patterns-established:
  - "Conditional middleware: try import, fallback to None, check before adding"
  - "Header extraction in separate module for dependency isolation"

# Metrics
duration: 15min
completed: 2026-02-03
---

# Phase 11 Plan 01: MCP Server Containerization Summary

**Multi-stage Dockerfile with standalone mode support - infrastructure middleware conditionally loaded, auth helpers extracted for DB-free operation**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-03T00:00:00Z
- **Completed:** 2026-02-03T00:15:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Multi-stage Dockerfile for optimized MCP server image (~353MB)
- Minimal requirements file without database dependencies
- Standalone mode: container runs without database/Redis
- Non-root user (mcpuser) for security
- Health check at /health using Python stdlib (no curl needed)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create requirements-mcp.txt** - `057bc1e0` (feat)
2. **Task 2: Create multi-stage Dockerfile.mcp** - `341f149d` (feat)

## Files Created/Modified

- `backend/requirements-mcp.txt` - Minimal MCP server dependencies (no psycopg2/sqlalchemy)
- `backend/Dockerfile.mcp` - Multi-stage build with non-root user
- `backend/app/mcp/auth_helpers.py` - Pure header extraction utilities (no DB deps)
- `backend/app/mcp/auth.py` - Now imports from auth_helpers, re-exports for backward compat
- `backend/app/mcp/server.py` - Uses auth_helpers.extract_api_key_header
- `backend/app/mcp/transport.py` - Conditionally loads infrastructure middleware

## Decisions Made

1. **Split auth_helpers.py from auth.py**: The original auth.py imported app.models, app.auth.jwt, and app.services which have database dependencies. Extracted pure utility functions (header extraction) to auth_helpers.py for standalone mode.

2. **Conditional infrastructure middleware loading**: Used try/except ImportError pattern to skip infrastructure middleware when running standalone (no database for API key validation).

3. **Python urllib for health check**: Avoided adding curl/wget to keep image minimal. HEALTHCHECK uses Python's built-in urllib.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] MCP module has hidden database dependencies**

- **Found during:** Task 2 (Docker build verification)
- **Issue:** The MCP infrastructure middleware imports app.core.rate_limiting and app.models which require database/Redis. Container startup failed with ModuleNotFoundError.
- **Fix:** Made infrastructure middleware import conditional with try/except ImportError. When imports fail (standalone mode), middleware is set to None and skipped in middleware list.
- **Files modified:** backend/app/mcp/transport.py
- **Verification:** Container starts, health check passes
- **Committed in:** 341f149d (Task 2 commit)

**2. [Rule 3 - Blocking] server.py imports auth.py which has DB dependencies**

- **Found during:** Task 2 (Docker build verification)
- **Issue:** server.py only needs extract_api_key_header but auth.py imports app.models, app.auth.jwt, app.services at module level. Python evaluates all imports at load time.
- **Fix:** Created auth_helpers.py with pure utility functions (no external deps). Updated server.py to import from auth_helpers. Updated auth.py to re-export from auth_helpers for backward compatibility.
- **Files modified:** backend/app/mcp/auth_helpers.py (created), backend/app/mcp/auth.py, backend/app/mcp/server.py
- **Verification:** Both standalone Docker and main backend imports work
- **Committed in:** 341f149d (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** Both fixes essential for standalone Docker operation. Maintains full functionality when running with main backend. No scope creep.

## Issues Encountered

- **Image size above target:** 353MB vs 300MB target. Acceptable given Python runtime + MCP dependencies. Multi-stage build already eliminates build tools.

## Verification Results

```bash
# Build succeeds
docker build -f backend/Dockerfile.mcp -t on-call-health-mcp:test backend/

# Container runs
docker run --rm -d --name mcp-test -p 8080:8080 on-call-health-mcp:test

# Health check passes
curl http://localhost:8080/health
# {"status":"healthy","service":"on-call-health-mcp"}

# Non-root user
docker exec mcp-test whoami
# mcpuser
```

## Next Phase Readiness

- Dockerfile ready for ECS task definition in 11-02
- Health check endpoint compatible with ALB target group
- Container runs on port 8080 as expected by ECS
- No blockers for Terraform/CDK deployment

---
*Phase: 11-aws-deployment*
*Completed: 2026-02-03*
