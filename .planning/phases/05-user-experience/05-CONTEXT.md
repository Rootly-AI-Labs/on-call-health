---
phase: 05-user-experience
created: 2026-02-02
status: complete
---

# Phase 5: User Experience - Implementation Context

**Phase Goal:** Users can see auth method for integrations, access helpful guidance, and switch between OAuth and token

**Requirements:** UX-04, SWITCH-01, SWITCH-02

## Auth Method Indicators

### Placement and Visibility
- **Display location:** Auth method badge appears directly on the integration card itself (Jira/Linear card on main integrations page)
- **Visibility:** Always visible when integration is connected, no hover/expand required
- **Disconnected state:** No badge shown on disconnected integrations (clean slate, no history)

### Badge Design
- **Content:** Show just the method type - simple "OAuth" or "API Token" text
- **Visual style:** Use color coding to distinguish methods
  - OAuth: One color (suggest: blue/primary)
  - API Token: Different color (suggest: gray/neutral)
- **No additional info:** Don't show renewal info, connected date, or other metadata in badge

### Implementation Notes
- Badge should be non-intrusive but clearly visible
- Color coding must meet accessibility contrast requirements
- Badge updates immediately when auth method changes

## Help Text and Guidance

### Decision Guidance
- **Timing:** No proactive guidance when user sees OAuth/Token choice
- **Access pattern:** "Only if they ask" - provide optional "Learn more" link
- **Content depth:** Keep it minimal - just key differences
  - OAuth: Auto-renews, uses standard OAuth flow
  - API Token: Manual rotation required, direct API key

### Switching Instructions
- **Location:** Show switching option directly on integration card (e.g., "Switch to Token" button on OAuth cards)
- **In-app vs docs:** Provide in-app switching UI, not just documentation links
- **Method indication:** Make it clear what the user is switching FROM and TO

### Data Preservation Warnings
- **Warning policy:** Always show "Your data is preserved" message when switching
- **Frequency:** Every switch shows the warning (not just first time)
- **Rationale:** Reassure users that workspace mappings, user correlations, and historical data remain intact

## Status and Empty States

### Switching Flow
- **Pattern:** Two-step process (not instant)
  1. User clicks "Switch to Token" → confirmation dialog → disconnect
  2. User manually clicks "Use API Token" → opens token form
- **Why two-step:** Gives user control, prevents accidental switches, matches mental model

### Loading States
- **Scope:** Card-level spinner during disconnect/reconnect
- **Rest of page:** Remains interactive (user can navigate away, view other integrations)
- **Duration:** Show spinner during disconnect API call and reconnect validation

### Error Handling
- **Failed switch policy:** Stay disconnected if validation fails
- **No rollback:** Don't automatically restore previous OAuth connection
- **User options:** Show error message, user can retry with corrected token or cancel
- **Why stay disconnected:** Makes it clear something went wrong, prevents confusion about which auth method is active

### Success Feedback
- **Method:** Toast notification only
- **Message:** Brief confirmation like "Switched to API Token" or "Switched to OAuth"
- **Badge update:** Auth method badge updates automatically, no animation/highlighting needed
- **Duration:** Standard 3-second toast (matches existing toast pattern)

## Downstream Guidance

### For Researcher/Planner
1. **Switching is NOT a single-click action** - it's disconnect + reconnect with new method
2. **Data preservation is critical** - all switch flows must preserve workspace mappings and user correlations
3. **No dedicated "switch" API endpoint** - reuse existing disconnect + connect endpoints
4. **Badge implementation** - likely a new component or prop on IntegrationCard
5. **Color coding** - define color constants for OAuth vs Token badges (consider theme)

### Implementation Priorities
1. Auth method badge display (core visibility requirement)
2. Disconnect confirmation with data preservation message
3. "Switch to X" button on connected cards
4. Card-level loading states during operations
5. Toast notifications for success
6. Optional "Learn more" link for decision guidance

### Testing Scenarios
- Switch OAuth → Token: Disconnect, verify data preserved, reconnect with token, verify badge updates
- Switch Token → OAuth: Disconnect, verify data preserved, reconnect with OAuth, verify badge updates
- Failed token validation during switch: Should stay disconnected, show error, allow retry
- Multiple rapid switches: Should handle cleanly without race conditions
- Visual: Badge colors meet contrast requirements, visible on light/dark themes

---

*Context gathering complete: 2026-02-02*
*Areas discussed: Auth method indicators, Help text and guidance, Status and empty states*
