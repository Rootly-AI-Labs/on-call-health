---
phase: 08-pypi-distribution
plan: 01
subsystem: mcp
tags: [pypi, mcp, hatchling, httpx, tenacity, aiobreaker]

# Dependency graph
requires:
  - phase: 05-rest-api-client
    provides: OnCallHealthClient with retry and circuit breaker
  - phase: 06-mcp-tools-refactor
    provides: REST-based MCP tools
provides:
  - Standalone PyPI package oncallhealth-mcp
  - pyproject.toml with hatchling build backend
  - CLI entry point for stdio/http transport
  - Self-contained MCP server code without backend dependencies
affects: [08-02, PyPI publishing, uvx execution]

# Tech tracking
tech-stack:
  added: [hatchling>=1.26]
  patterns: [src layout for PyPI packages, CLI entry point pattern]

key-files:
  created:
    - packages/oncallhealth-mcp/pyproject.toml
    - packages/oncallhealth-mcp/LICENSE
    - packages/oncallhealth-mcp/README.md
    - packages/oncallhealth-mcp/src/oncallhealth_mcp/__init__.py
    - packages/oncallhealth-mcp/src/oncallhealth_mcp/cli.py
    - packages/oncallhealth-mcp/src/oncallhealth_mcp/server.py
    - packages/oncallhealth-mcp/src/oncallhealth_mcp/auth.py
    - packages/oncallhealth-mcp/src/oncallhealth_mcp/normalizers.py
    - packages/oncallhealth-mcp/src/oncallhealth_mcp/client/*.py
  modified: []

key-decisions:
  - "Package name oncallhealth-mcp with underscore module oncallhealth_mcp"
  - "hatchling build backend for modern PyPI compatibility"
  - "Flexible dependency bounds (>=X.Y,<Z.0) for compatibility"
  - "CLI validates ONCALLHEALTH_API_KEY before starting"

patterns-established:
  - "PyPI src layout: packages/{name}/src/{module}/"
  - "CLI entry point: oncallhealth_mcp.cli:main"
  - "Environment variable config: ONCALLHEALTH_API_KEY, ONCALLHEALTH_API_URL"

# Metrics
duration: 8min
completed: 2026-02-02
---

# Phase 8 Plan 1: Package Structure Summary

**Standalone PyPI package oncallhealth-mcp with hatchling build, CLI entry point, and all MCP server code self-contained**

## Performance

- **Duration:** 8 min
- **Started:** 2026-02-02T22:46:00Z
- **Completed:** 2026-02-02T22:54:00Z
- **Tasks:** 2 (+1 deviation)
- **Files modified:** 14

## Accomplishments
- Created PyPI-compatible package structure at packages/oncallhealth-mcp/
- pyproject.toml with hatchling build, Python 3.10-3.13 support
- CLI entry point supporting --transport (stdio/http), --verbose flags
- All MCP source code copied with import paths updated to oncallhealth_mcp.*
- No backend app dependencies (removed SQLAlchemy imports from auth.py)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create package structure and pyproject.toml** - `7e741585` (feat)
2. **Task 2: Copy and adapt MCP source code** - `3a705f74` (feat)
3. **Deviation: Add CLI entry point** - `dbc1eec0` (feat)

## Files Created/Modified

### Package Root
- `packages/oncallhealth-mcp/pyproject.toml` - Package metadata, dependencies, entry points
- `packages/oncallhealth-mcp/LICENSE` - MIT license
- `packages/oncallhealth-mcp/README.md` - Placeholder (detailed in Plan 02)

### Module Files
- `src/oncallhealth_mcp/__init__.py` - Package entry with __version__ and exports
- `src/oncallhealth_mcp/cli.py` - CLI entry point with argparse
- `src/oncallhealth_mcp/server.py` - FastMCP server with all tools
- `src/oncallhealth_mcp/auth.py` - Header extraction (no SQLAlchemy)
- `src/oncallhealth_mcp/normalizers.py` - REST response transformers

### Client Subpackage
- `src/oncallhealth_mcp/client/__init__.py` - Public exports
- `src/oncallhealth_mcp/client/base.py` - OnCallHealthClient
- `src/oncallhealth_mcp/client/config.py` - ClientConfig with env vars
- `src/oncallhealth_mcp/client/exceptions.py` - MCP exception hierarchy
- `src/oncallhealth_mcp/client/retry.py` - Tenacity retry decorator
- `src/oncallhealth_mcp/client/circuit_breaker.py` - aiobreaker integration
- `src/oncallhealth_mcp/client/health.py` - Connection pool monitor

## Decisions Made

1. **Package name oncallhealth-mcp** - Matches user decision in CONTEXT.md
2. **hatchling build backend** - Modern, fast, recommended for new packages
3. **Flexible version bounds** - `>=X.Y.Z,<2.0` allows patch/minor upgrades
4. **CLI validates API key** - Fails fast with helpful error message

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added CLI entry point module**
- **Found during:** Task 1 completion
- **Issue:** pyproject.toml references oncallhealth_mcp.cli:main but cli.py didn't exist
- **Fix:** Created cli.py with argparse, transport flag, validation
- **Files modified:** packages/oncallhealth-mcp/src/oncallhealth_mcp/cli.py
- **Verification:** python -m py_compile passes
- **Committed in:** dbc1eec0

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Essential for package functionality. CLI entry point was referenced but not specified in task list.

## Issues Encountered
None - all files copied and adapted successfully.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Package structure complete, ready for Plan 02 (README and documentation)
- Can build locally with `pip install -e packages/oncallhealth-mcp`
- Not yet ready for PyPI publish (needs README, tests)

---
*Phase: 08-pypi-distribution*
*Completed: 2026-02-02*
