---
phase: 04-linear-token-integration
plan: 01
subsystem: api
tags: [linear, api-tokens, encryption, oauth, fernet]

# Dependency graph
requires:
  - phase: 01-backend-foundation
    provides: Token encryption infrastructure and TokenManager
  - phase: 02-validation-infrastructure
    provides: IntegrationValidator with validate_manual_token method
  - phase: 03-jira-token-integration
    provides: Pattern for manual token save endpoints

provides:
  - POST /api/linear/connect-manual endpoint for manual API tokens
  - Linear workspace mapping with registered_via='manual'
  - Linear user correlation enforcement (one-to-one mapping)
  - Backend token re-validation before save

affects: [04-02-frontend-token-ui, future-linear-features]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Backend re-validates all manual tokens (never trust client validation)
    - Manual tokens set token_source='manual' and token_expires_at=None
    - Workspace mapping created atomically with registered_via field
    - Linear account removal from other users enforces one-to-one mapping

key-files:
  created: []
  modified:
    - backend/app/api/endpoints/linear.py

key-decisions:
  - "Backend re-validates all tokens (never trust frontend validation)"
  - "Manual tokens set token_expires_at=None (no auto-expiry)"
  - "Workspace info fetched via GraphQL before save (required for LinearIntegration)"
  - "Enforces one-to-one Linear account mapping across organization users"

patterns-established:
  - "Linear manual token flow: simpler than Jira (no site_url field needed)"
  - "Uses same IntegrationValidator interface as Jira for consistency"
  - "Workspace mapping creation follows OAuth callback pattern"

# Metrics
duration: 1min
completed: 2026-02-02
---

# Phase 04 Plan 01: Linear Token Integration Summary

**POST /api/linear/connect-manual endpoint validates, encrypts, and saves Linear API tokens with workspace mapping and user correlation**

## Performance

- **Duration:** 1 min
- **Started:** 2026-02-02T18:44:03Z
- **Completed:** 2026-02-02T18:45:05Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Created POST /api/linear/connect-manual endpoint following Jira pattern
- Backend re-validates tokens via IntegrationValidator before save (security)
- Encrypts tokens with Fernet (same security level as OAuth tokens)
- Creates LinearWorkspaceMapping with registered_via='manual'
- Creates/updates UserCorrelation for Linear user
- Enforces one-to-one Linear account mapping across organization

## Task Commits

Each task was committed atomically:

1. **Task 1: Add POST /connect-manual endpoint to linear.py** - `8d6fa8bd` (feat)

## Files Created/Modified
- `backend/app/api/endpoints/linear.py` - Added POST /connect-manual endpoint (193 lines)

## Decisions Made
- Backend re-validates all manual tokens (never trust client validation) - security requirement
- Manual tokens set token_source='manual' and token_expires_at=None (no auto-expiry)
- Workspace info fetched via GraphQL before save (required for LinearIntegration schema)
- Linear account removed from other users before assignment (enforces one-to-one mapping)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Backend endpoint complete and ready for frontend integration (Plan 04-02).

Frontend can now:
- Call POST /api/linear/connect-manual with token
- Receive validated integration response
- Display success/error states

Blockers: None

---
*Phase: 04-linear-token-integration*
*Completed: 2026-02-02*
