---
phase: 02-validation-infrastructure
plan: 01
subsystem: api
tags: [validation, jira, linear, error-handling, httpx, security]

# Dependency graph
requires:
  - phase: 01-backend-foundation
    provides: Integration models and token encryption utilities
provides:
  - Token validation endpoints for Jira and Linear
  - Platform-specific error message maps with actionable guidance
  - IntegrationValidator service for pre-save token validation
affects: [02-validation-infrastructure, frontend-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Platform-specific error messages with error_type categorization
    - Pre-save token validation pattern for manual API tokens
    - Structured error responses (message, action, help_url)

key-files:
  created:
    - backend/app/core/error_messages.py
  modified:
    - backend/app/services/integration_validator.py
    - backend/app/api/endpoints/jira.py
    - backend/app/api/endpoints/linear.py

key-decisions:
  - "Format validation before API call (fast fail on invalid tokens)"
  - "Return user_info on success for UI display"
  - "Never log or include actual tokens in error messages (security)"
  - "Use Bearer auth for Jira PAT (not Basic auth)"

patterns-established:
  - "Structured validation response: {valid, error, error_type, help_url, action, user_info}"
  - "Error type categorization: authentication, permissions, network, format, site_url"
  - "Platform-specific error messages guide users to fix issues"

# Metrics
duration: 2min
completed: 2026-02-02
---

# Phase 2 Plan 1: Token Validation Endpoints Summary

**Pre-save validation endpoints for Jira and Linear manual tokens with platform-specific error guidance**

## Performance

- **Duration:** 2 minutes
- **Started:** 2026-02-02T03:01:26Z
- **Completed:** 2026-02-02T03:03:41Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments

- Platform-specific error message maps with 5 Jira and 4 Linear error types
- Validation service methods for Jira PAT and Linear API key validation
- POST endpoints at /api/jira/validate-token and /api/linear/validate-token
- Structured error responses with actionable next steps and help URLs

## Task Commits

Each task was committed atomically:

1. **Task 1: Create platform-specific error message maps** - `c8c10a50` (feat)
2. **Task 2: Add validate_manual_token to IntegrationValidator** - `821ca35d` (feat)
3. **Task 3: Add validation endpoints to Jira and Linear** - `cdd20865` (feat)

## Files Created/Modified

- `backend/app/core/error_messages.py` - Platform-specific error messages with JIRA_ERROR_MESSAGES (5 types), LINEAR_ERROR_MESSAGES (4 types), and get_error_response() helper
- `backend/app/services/integration_validator.py` - Added validate_manual_token(), _validate_jira_manual_token(), _validate_linear_manual_token()
- `backend/app/api/endpoints/jira.py` - Added POST /validate-token endpoint for Jira PAT validation
- `backend/app/api/endpoints/linear.py` - Added POST /validate-token endpoint for Linear API key validation

## Decisions Made

1. **Format validation before API call** - Validate token format (e.g., Linear keys must start with 'lin_api_') before making network requests for fast failure
2. **Return user_info on success** - Include display_name, email, and platform-specific ID in success response for UI display
3. **Never log tokens** - Log only validation success/failure status, never the actual token value (security requirement)
4. **Bearer auth for Jira PAT** - Use `Authorization: Bearer {token}` instead of Basic auth for Jira Personal Access Tokens
5. **Site URL normalization** - Auto-prepend https:// to Jira site URLs if missing

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Validation endpoints ready for frontend integration
- Error messages provide actionable guidance for users to fix token issues
- Supports both Jira (requires site_url) and Linear (no site_url needed)
- Ready for Phase 2 Plan 2: Frontend validation UI implementation

---
*Phase: 02-validation-infrastructure*
*Completed: 2026-02-02*
