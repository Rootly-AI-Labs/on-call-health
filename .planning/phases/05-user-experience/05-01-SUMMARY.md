---
phase: 05-user-experience
plan: 01
subsystem: ui
tags: [react, radix-ui, badges, dialogs, auth-switching]

# Dependency graph
requires:
  - phase: 04-linear-token-integration
    provides: token_source field on integrations for displaying OAuth vs API Token
  - phase: 02-validation-infrastructure
    provides: StatusIndicator component pattern
provides:
  - AuthMethodBadge component for displaying OAuth vs API Token
  - AuthMethodSwitchDialog for confirming auth method switches
  - Connected cards show auth method badge and Switch to X button
affects: [05-02-switch-orchestration, integration-ui]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auth method badges use color coding: blue for OAuth, gray for API Token"
    - "Switch buttons shown in card footer with disconnect button"
    - "Data preservation message shown in all switch confirmations"

key-files:
  created:
    - frontend/src/app/integrations/components/AuthMethodBadge.tsx
    - frontend/src/app/integrations/dialogs/AuthMethodSwitchDialog.tsx
  modified:
    - frontend/src/app/integrations/components/JiraConnectedCard.tsx
    - frontend/src/app/integrations/components/LinearConnectedCard.tsx

key-decisions:
  - "Auth method badge always visible (not in dropdown) for immediate visibility"
  - "Switch button hidden when token has error (clean state required for switching)"
  - "Disconnect button moved to footer alongside switch button"
  - "Auth Method row removed from details grid (redundant with badge)"
  - "Blue color for OAuth badge (RefreshCw icon indicates auto-renewal)"
  - "Neutral gray for API Token badge (Key icon)"

patterns-established:
  - "AuthMethodBadge is standalone component with OAuth/API Token variants"
  - "AuthMethodSwitchDialog follows existing JiraDisconnectDialog pattern"
  - "Data preservation message uses blue info box (consistent with plan context)"
  - "Switch buttons use ArrowLeftRight icon with blue styling"

# Metrics
duration: 4min
completed: 2026-02-02
---

# Phase 5 Plan 1: Auth Method Visibility Summary

**Auth method badges (OAuth vs API Token) and switch buttons added to Jira and Linear connected cards with data preservation confirmation dialog**

## Performance

- **Duration:** 4 min
- **Started:** 2026-02-02T22:35:41Z
- **Completed:** 2026-02-02T22:39:34Z
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- Created AuthMethodBadge component with OAuth (blue) and API Token (gray) color-coded variants
- Created AuthMethodSwitchDialog with data preservation reassurance message
- Updated Jira and Linear connected cards to display auth method badges prominently
- Added "Switch to X" buttons in card footers (hidden when token has error)
- Reorganized card layout with footer buttons section

## Task Commits

Each task was committed atomically:

1. **Task 1: Create AuthMethodBadge and AuthMethodSwitchDialog components** - `7bf8650` (feat)
2. **Task 2: Add auth method badge and switch button to JiraConnectedCard** - `0c433c3` (feat)
3. **Task 3: Add auth method badge and switch button to LinearConnectedCard** - `b4e5c94` (feat)

## Files Created/Modified
- `frontend/src/app/integrations/components/AuthMethodBadge.tsx` - Standalone badge component with OAuth/API Token variants and icons
- `frontend/src/app/integrations/dialogs/AuthMethodSwitchDialog.tsx` - Reusable switch confirmation dialog with data preservation message
- `frontend/src/app/integrations/components/JiraConnectedCard.tsx` - Added badge and switch button, reorganized layout
- `frontend/src/app/integrations/components/LinearConnectedCard.tsx` - Added badge and switch button, reorganized layout

## Decisions Made
- Auth method badge placed next to integration title (always visible, not requiring dropdown interaction)
- Badge uses RefreshCw icon for OAuth (signals auto-renewal) and Key icon for API Token
- Blue color scheme for OAuth (bg-blue-100, text-blue-700) to match existing active/connected patterns
- Neutral gray for API Token (bg-neutral-200, text-neutral-700) to distinguish from OAuth
- Switch button hidden when hasTokenError=true (prevents switching from invalid state)
- Disconnect button moved from header to footer to group with switch button
- Auth Method details grid row removed (redundant with always-visible badge)
- Data preservation info box uses blue-50 background with AlertCircle icon for consistency

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - all components created successfully following existing patterns.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for Phase 5 Plan 2 (switch orchestration):
- AuthMethodBadge component available for import
- AuthMethodSwitchDialog ready to be wired up to disconnect handlers
- Connected cards expose onSwitchAuth callback prop for parent component integration
- UI components complete, awaiting handler logic

---
*Phase: 05-user-experience*
*Completed: 2026-02-02*
