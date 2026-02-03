# Phase 4: Linear Token Integration - Context

**Gathered:** 2026-02-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable users to connect Linear integration using an API token as an alternative to OAuth. Users see both OAuth and API Token connection options on the Linear card. The API Token flow validates tokens in real-time (using Phase 2 infrastructure), saves immediately after validation, and starts background data sync. The experience should be quick and frictionless while providing minimal necessary guidance.

**Key difference from Jira:** Linear only requires the token - no site URL field needed.

</domain>

<decisions>
## Implementation Decisions

### Connection Method Presentation

- **Card layout:** Always show both connection buttons directly on the Linear integration card (no expand/click to reveal)
- **Button style:** Two separate buttons with equal visual weight - neither method is favored
  - "Connect with OAuth" button
  - "Use API Token" button
- **No hierarchy:** Don't emphasize one method over the other - user decides based on their needs
- **Button positioning:** Side-by-side or stacked (Claude's discretion based on card width/responsive design)
- **Consistency:** Same pattern as Jira (Phase 3)

### Help Text and Guidance

- **Minimal approach:** Just provide a link to Linear's token creation page
- **Location:** Keep the collapsible "How to get your Linear API key" section from current implementation
- **Content:** Just the bare link inside the collapsible - "Create your API key at Linear" (linked to https://linear.app/settings/api)
- **No instructions:** Remove any multi-step numbered instructions currently in the form
- **Assumption:** Users choosing API Token can follow Linear's documentation
- **Consistency:** Same minimal approach as Jira

### Authentication Method Warning

- **No upfront warning:** Don't show comparison or differences between OAuth and API Token before user chooses
- **No per-method warning:** Don't show warning when user selects API Token path
- **Documentation only:** Information about OAuth auto-refresh vs manual token rotation available in help docs if users look for it
- **Rationale:** Users choosing API Token likely understand the trade-offs - don't interrupt the flow
- **Consistency:** Same no-warning approach as Jira

### Token Validation and Save Flow

- **Auto-validate:** Token validation happens automatically as user types (using Phase 2 useValidation hook)
- **Save behavior:** Immediately save and close after token validates successfully
  - No intermediate "Save Integration" button click required
  - No optional nickname field
  - No preview permissions step
- **Visual feedback:** Show brief toast notification after save
  - Message: "Linear connected!"
  - Duration: 3 seconds
  - Style: Success toast (green)
- **Form closure:** Close the token setup form and return to integrations list immediately after save
- **Consistency:** Same auto-save flow as Jira

### Form Layout and Simplification

- **Spacing:** Keep current spacing and padding from existing LinearManualSetupForm
- **Fields removed:**
  - Nickname/integration name field (was shown after validation)
  - Multi-step instructions in collapsible section (replace with just link)
- **Fields kept:**
  - Token input (with show/hide toggle)
  - Collapsible help section (simplified to just link)
- **Layout consistency:** Maintain same card structure as existing form for visual consistency
- **Linear simplicity:** No site URL field needed (simpler than Jira form)

### Data Synchronization

- **Sync timing:** Start background sync immediately after token is saved
- **No indication:** Silent background sync - no loading states or progress notifications
- **User experience:** User sees success toast, form closes, data appears when ready
- **No prompts:** Don't ask user "Sync now?" - just do it
- **Consistency:** Same background sync approach as Jira

### Backend Integration (Save Endpoint)

- **New endpoint needed:** POST /api/linear/connect-manual (or similar)
- **Accepts:** { token, userInfo? }
- **No site_url:** Linear doesn't need site URL (unlike Jira)
- **Validation:** Token should already be validated by frontend (Phase 2), but backend validates again
- **Encryption:** Use same Fernet encryption as OAuth tokens (Phase 1 foundation)
- **Token source:** Set token_source='manual' in database
- **Returns:** Integration object with { id, token_valid, token_source, ... }

### Claude's Discretion

- Exact API endpoint naming and structure
- Button ordering (OAuth first or Token first)
- Button responsive layout (stacked vs side-by-side at different breakpoints)
- Error handling specifics for save failures
- Exact toast notification positioning and animation
- Background sync implementation details (job queue, polling interval, etc.)

</decisions>

<specifics>
## Specific Ideas

- **Same as Jira:** Apply all Phase 3 decisions to Linear for consistency
- **Simpler form:** Linear form only has token field (no site URL) - naturally simpler
- "Equal weight" buttons - no visual hierarchy between OAuth and Token options
- "Just the bare link" in help section - minimal guidance philosophy
- "Background sync, no indication" - don't interrupt user flow with sync status
- Keep existing validation infrastructure from Phase 2 (useValidation hook, StatusIndicator component)
- LinearManualSetupForm component already exists - adapt it for simplified auto-save flow (same as Jira)

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within phase scope. Applying Phase 3 pattern to Linear.

</deferred>

---

*Phase: 04-linear-token-integration*
*Context gathered: 2026-02-02*
