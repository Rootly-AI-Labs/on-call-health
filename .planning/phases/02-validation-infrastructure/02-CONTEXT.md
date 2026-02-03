# Phase 2: Validation Infrastructure - Context

**Gathered:** 2026-02-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a type-aware token validation system that checks if tokens work before saving them to the database. The system handles OAuth tokens (which can be refreshed) and manual API tokens (which cannot be refreshed) differently. Validation runs during initial setup and periodically during use (with caching). Users see clear validation status and receive specific error messages when validation fails.

</domain>

<decisions>
## Implementation Decisions

### Validation Timing and Flow

- **Initial setup:** Validate immediately after user enters token (before they click save)
- **Save interaction:** If validation still running when user clicks save, wait for validation to complete then save (spinner on save button)
- **Periodic validation:** Validate on each token use, with 15-minute cache
- **Reconnection flow:** When user reconnects (switching OAuth to token or updating token), clear old connection immediately, then validate new token

### Error Messaging Strategy

- **Specificity:** Very specific error messages - different message for each failure type:
  - Authentication failures (invalid token, wrong credentials)
  - Permission failures (token lacks required scopes)
  - Network failures (can't reach API, timeout)
  - Format failures (malformed token, wrong token type)

- **Platform-specific:** Jira errors reference Jira concepts (Personal Access Token, Jira site), Linear errors reference Linear concepts (Personal API Key, workspace)

- **Error message content includes:**
  - Direct link to platform documentation for creating tokens
  - List of required permissions/scopes
  - Actionable next steps (e.g., "Generate a new token with read:issue permission")

- **Post-setup failures:** Claude's discretion on notification strategy (in-app, email, or both)

### Visual Status Indicators

- **Connection states to display:**
  - Connected (working) - token is valid
  - Validating (in progress) - currently checking token
  - Error (failed) - validation failed or token doesn't work
  - Disconnected (not set up) - integration not configured

- **Consistency principle:** Use same UI/UX patterns as existing OAuth integrations. If improvements are made, apply to all integrations (not just Jira/Linear)

- **Indicator locations:**
  - Integrations list page - status for each integration
  - Integration setup modal - live status during token entry/validation
  - Notification system - alerts for validation failures
  - Popup messages - contextual status updates

- **Real-time updates:** Status indicators update in real-time via WebSocket/polling, not just on page refresh

- **Auth method display:** Status text includes auth method - "Connected via OAuth" or "Connected via API Token"

### Claude's Discretion

- Exact validation API call implementation
- Cache invalidation strategy details
- WebSocket vs polling for real-time updates
- Notification priority and delivery timing for post-setup failures
- Specific UI component choices (as long as they match existing patterns)

</decisions>

<specifics>
## Specific Ideas

- "Look at what's already done, use same practice" - Validation infrastructure should feel like a natural extension of existing OAuth flows
- "Make sure the same UI/UX applies to all integrations (not just Jira/Linear)" - Any improvements should benefit the entire integrations system
- "We also have a notification system, we could share stuff there. As well as a little popup message" - Leverage existing notification infrastructure

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope.

</deferred>

---

*Phase: 02-validation-infrastructure*
*Context gathered: 2026-02-01*
