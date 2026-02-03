# Phase 4: Frontend UI & UX - Context

**Gathered:** 2026-01-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Build user-facing web interface for API key management in the dashboard. Users can create keys (with name and optional expiration), view their keys in a table (with masked display), copy keys once after creation, and revoke keys with confirmation. Navigation, routing, and all UI components for the complete key management flow.

</domain>

<decisions>
## Implementation Decisions

### Claude's Full Discretion

User has granted Claude complete discretion to make all UI/UX decisions based on:
- Existing dashboard patterns and conventions in the codebase
- Next.js 16 and React best practices
- Tailwind CSS styling that matches the current design system
- Accessibility and responsive design standards

**Areas with full discretion:**
- Page layout and structure (header, sections, spacing)
- Navigation placement (user dropdown, sidebar, or settings section)
- Route structure (`/dashboard/api-keys` or other appropriate path)
- Creation flow (modal vs page, single-step vs wizard)
- Form design (field layout, validation feedback, error handling)
- Success state (how to show the full key once and only once)
- Copy-to-clipboard interaction (button placement, feedback mechanism)
- Key list table design (columns, density, sorting, filtering)
- Masked key display format (`och_live_****1234` or similar)
- Empty state messaging and design
- Revoke confirmation dialog (content, button placement, warnings)
- Loading states and skeleton screens
- Toast notifications vs inline feedback
- Mobile responsive behavior
- Color scheme and typography

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches that match the existing On-Call Health dashboard.

**Constraints from requirements:**
- Must show full key exactly once (after creation)
- Must provide copy-to-clipboard functionality
- Must require confirmation before revocation
- Must support optional expiration date selection
- Must display keys in a table/list format
- Must show masked keys (not full keys) in the list
- Security warning: "This is the only time you'll see this key"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-frontend-ui-ux*
*Context gathered: 2026-01-31*
