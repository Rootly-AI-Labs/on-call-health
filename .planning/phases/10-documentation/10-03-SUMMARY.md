---
phase: 10-documentation
plan: 03
subsystem: docs
tags: [deprecation, migration, documentation, legacy]

# Dependency graph
requires:
  - phase: 10-01
    provides: DEPLOYMENT_SSE.md target for deprecation redirects
  - phase: 10-02
    provides: MIGRATION.md, DEPLOYMENT_AWS.md targets for deprecation redirects
provides:
  - Legacy docs with deprecation notices redirecting to v1.1 guides
  - Clear user path from old documentation to new architecture docs
affects: [users, onboarding]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deprecation notice pattern: blockquote at top of legacy files"

key-files:
  created: []
  modified:
    - docs/MCP_SETUP.md
    - docs/MCP_CLAUDE_CODE_SETUP.md
    - docs/MCP_PRODUCTION_READY.md

key-decisions:
  - "Blockquote format for deprecation notices (consistent with migration guide)"
  - "Different redirect targets for production guide (AWS vs PyPI)"

patterns-established:
  - "Legacy doc deprecation: blockquote notice, horizontal rule, original content"

# Metrics
duration: 2min
completed: 2026-02-03
---

# Phase 10 Plan 03: Legacy Documentation Deprecation Summary

**Deprecation notices added to three legacy MCP docs, redirecting users to v1.1 SSE/PyPI/AWS documentation**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-03
- **Completed:** 2026-02-03
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- MCP_SETUP.md deprecated with links to DEPLOYMENT_SSE.md, oncallhealth-mcp README, and MIGRATION.md
- MCP_CLAUDE_CODE_SETUP.md deprecated with same links as general setup guide
- MCP_PRODUCTION_READY.md deprecated with links to DEPLOYMENT_SSE.md, DEPLOYMENT_AWS.md, and MIGRATION.md

## Task Commits

Note: docs/*.md files are gitignored per project policy. No commits created.

1. **Task 1: Add Deprecation Notice to MCP_SETUP.md** - (not committed, gitignored)
2. **Task 2: Add Deprecation Notice to MCP_CLAUDE_CODE_SETUP.md** - (not committed, gitignored)
3. **Task 3: Add Deprecation Notice to MCP_PRODUCTION_READY.md** - (not committed, gitignored)

## Files Created/Modified
- `docs/MCP_SETUP.md` - Added deprecation notice pointing to v1.1 guides (SSE, PyPI, Migration)
- `docs/MCP_CLAUDE_CODE_SETUP.md` - Added deprecation notice pointing to v1.1 guides (SSE, PyPI, Migration)
- `docs/MCP_PRODUCTION_READY.md` - Added deprecation notice pointing to v1.1 guides (SSE, AWS, Migration)

## Decisions Made
- Used blockquote format for deprecation notices (matches MIGRATION.md breaking change notice style)
- MCP_PRODUCTION_READY.md links to AWS deployment instead of PyPI (more relevant for production deployments)
- Original content preserved below horizontal rule for reference

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- docs/*.md files are gitignored per project policy; files modified locally but not committed

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 10 (Documentation) complete
- All v1.1 documentation in place:
  - DEPLOYMENT_SSE.md (10-01)
  - MIGRATION.md, DEPLOYMENT_AWS.md (10-02)
  - Legacy docs deprecated (10-03)
- Ready for Phase 11 (AWS Deployment IaC)

---
*Phase: 10-documentation*
*Completed: 2026-02-03*
