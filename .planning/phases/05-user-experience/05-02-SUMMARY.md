---
phase: 05-user-experience
plan: 02
subsystem: ui
tags: [react, radix-ui, dialogs, auth-switching, toast, state-management]

# Dependency graph
requires:
  - phase: 05-user-experience
    plan: 01
    provides: AuthMethodBadge and AuthMethodSwitchDialog components
  - phase: 04-linear-token-integration
    provides: token_source field and disconnect handlers for Linear
  - phase: 03-jira-token-integration
    provides: token_source field and disconnect handlers for Jira
provides:
  - Complete auth method switch flow with state management
  - Data preservation messaging in all disconnect scenarios
  - Toast feedback for successful switches
  - Integration between connected cards and switch dialogs
affects: [integration-ui, user-onboarding, auth-switching]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Switch flow uses two-step pattern: disconnect then user manually reconnects"
    - "Data preservation message shown in both disconnect and switch dialogs"
    - "Toast notifications guide user to reconnect after disconnect"
    - "Switch handlers reuse existing disconnect logic"

key-files:
  created: []
  modified:
    - frontend/src/app/integrations/dialogs/JiraDisconnectDialog.tsx
    - frontend/src/app/integrations/dialogs/LinearDisconnectDialog.tsx
    - frontend/src/app/integrations/page.tsx

key-decisions:
  - "Switch flow disconnects and shows toast, user manually reconnects (not automatic reconnect)"
  - "Data preservation message uses consistent blue info box styling across all dialogs"
  - "Toast message specifies new auth method (OAuth or API Token) to guide user"
  - "Switch handlers reuse existing handleJiraDisconnect/handleLinearDisconnect logic"

patterns-established:
  - "Data preservation info box: bg-blue-50 with AlertCircle icon"
  - "Switch dialog state managed alongside disconnect dialog state"
  - "onSwitchAuth callback prop pattern matches onDisconnect pattern"

# Metrics
duration: 3min
completed: 2026-02-03
---

# Phase 5 Plan 2: Switch Flow Orchestration Summary

**Complete auth method switch flow with data preservation messaging, state management, toast feedback, and seamless integration between connected cards and switch dialogs**

## Performance

- **Duration:** 3 min
- **Started:** 2026-02-03T03:43:04Z
- **Completed:** 2026-02-03T03:46:56Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Added data preservation reassurance to Jira and Linear disconnect dialogs
- Wired complete switch flow in integrations page with state management
- Created handleJiraSwitch and handleLinearSwitch handlers that disconnect and guide user
- Connected AuthMethodSwitchDialog to both Jira and Linear integrations
- Users can now switch between OAuth and API Token authentication methods

## Task Commits

Each task was committed atomically:

1. **Task 1: Add data preservation message to disconnect dialogs** - `422dd58` (feat)
2. **Task 2: Wire switch flow in integrations page** - `b8925c0` (feat)
3. **Task 3: Verify complete switch flow works** - No commit (verification only)

## Files Created/Modified
- `frontend/src/app/integrations/dialogs/JiraDisconnectDialog.tsx` - Added data preservation info box with AlertCircle icon
- `frontend/src/app/integrations/dialogs/LinearDisconnectDialog.tsx` - Added data preservation info box with AlertCircle icon
- `frontend/src/app/integrations/page.tsx` - Added switch dialog state, handlers, and rendered AuthMethodSwitchDialog components

## Decisions Made
- Switch flow is two-step (disconnect → user manually reconnects) not automatic reconnect
- Data preservation message appears in both standard disconnect and auth method switch dialogs
- Toast notification after disconnect specifies the new auth method (OAuth or API Token) to guide user
- Switch handlers reuse existing disconnect handlers (DRY principle)
- Integration remains disconnected if user cancels reconnection (no rollback to previous method)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components integrated successfully following existing patterns.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Phase 5 Plan 3 (final UI polish and edge cases):
- Complete switch flow functional (OAuth ↔ API Token for both Jira and Linear)
- Data preservation messaging consistent across all disconnect scenarios
- Toast feedback guides users through switch process
- All components properly wired and state managed
- No blocking issues or concerns

---
*Phase: 05-user-experience*
*Completed: 2026-02-03*
