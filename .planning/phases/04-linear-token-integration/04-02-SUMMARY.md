---
phase: 04-linear-token-integration
plan: 02
subsystem: ui
tags: [linear, api-tokens, react, auto-save, dual-auth]

# Dependency graph
requires:
  - phase: 02-validation-infrastructure
    provides: useValidation hook for real-time token validation
  - phase: 03-jira-token-integration
    provides: Pattern for dual-button cards and auto-save forms
  - phase: 04-01
    provides: Backend POST /api/linear/connect-manual endpoint

provides:
  - LinearIntegrationCard with dual OAuth/Token buttons
  - LinearManualSetupForm with auto-save flow
  - handleLinearManualConnect handler function
  - Complete Linear manual token connection UX

affects: [future-integrations-ui, token-management-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Dual-button cards with equal visual weight (flex-1)
    - Auto-save forms that close on success without manual Save button
    - Simplified help sections with just API settings link
    - Toast notifications for integration success

key-files:
  created: []
  modified:
    - frontend/src/app/integrations/handlers/linear-handlers.ts
    - frontend/src/app/integrations/components/LinearIntegrationCard.tsx
    - frontend/src/app/integrations/components/LinearManualSetupForm.tsx
    - frontend/src/app/integrations/page.tsx

key-decisions:
  - "Auto-save triggers when validation succeeds (no manual Save button)"
  - "Dual buttons have equal visual weight via flex-1 styling"
  - "Help section simplified to single Linear API settings link"
  - "Form shows 'Saving...' status during auto-save"
  - "Nickname field removed (not needed for API token flow)"

patterns-established:
  - "Linear simpler than Jira: only token field required (no site_url)"
  - "Same auto-save pattern across all manual token integrations"
  - "Consistent neutral colors for Linear brand (border-neutral-300, bg-neutral-50)"

# Metrics
duration: 4min
completed: 2026-02-02
---

# Phase 04 Plan 02: Linear Token Integration Summary

**Dual OAuth/Token connection options with frictionless auto-save flow for Linear API tokens**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-03T01:55:34Z
- **Completed:** 2026-02-03T01:59:02Z
- **Tasks:** 4
- **Files modified:** 4

## Accomplishments
- LinearIntegrationCard shows both OAuth and API Token buttons with equal visual weight
- LinearManualSetupForm auto-saves when validation succeeds and shows success toast
- handleLinearManualConnect handler calls backend POST /api/linear/connect-manual
- Complete Linear manual token connection flow integrated into integrations page

## Task Commits

Each task was committed atomically:

1. **Task 1: Add handleLinearManualConnect handler** - `9d311a79` (feat)
2. **Task 2: Update LinearIntegrationCard with dual buttons** - `62ef6c95` (feat)
3. **Task 3: Update LinearManualSetupForm with auto-save and simplified help** - `2ce563cc` (feat)
4. **Task 4: Wire up components in page.tsx** - `db943e38` (feat)

## Files Created/Modified
- `frontend/src/app/integrations/handlers/linear-handlers.ts` - Added handleLinearManualConnect handler
- `frontend/src/app/integrations/components/LinearIntegrationCard.tsx` - Added dual OAuth/Token buttons
- `frontend/src/app/integrations/components/LinearManualSetupForm.tsx` - Implemented auto-save flow
- `frontend/src/app/integrations/page.tsx` - Wired up Linear manual token flow

## Decisions Made
- Auto-save triggers when validation succeeds (no manual Save button) - consistent with Jira pattern
- Dual buttons have equal visual weight via flex-1 styling - no hierarchy between methods
- Help section simplified to single Linear API settings link - minimal guidance philosophy
- Form shows 'Saving...' status during auto-save - user feedback without blocking
- Nickname field removed (not needed for API token flow) - simpler UX

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 4 complete - Linear token integration frontend finished.

Users can now:
- See both OAuth and API Token connection options on Linear card
- Enter Linear API token with real-time validation
- Experience frictionless auto-save flow (validates → saves → closes → shows toast)
- Access simplified help with link to Linear API settings

Complete flow:
1. Click "Use API Token" button
2. Form opens with token field
3. Type token → auto-validates
4. Validation succeeds → auto-saves
5. Toast "Linear connected!" → form closes
6. Linear integration active

Blockers: None

---
*Phase: 04-linear-token-integration*
*Completed: 2026-02-02*
