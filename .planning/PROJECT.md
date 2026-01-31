# On-Call Health

## What This Is

On-Call Health is a burnout detection platform that analyzes on-call patterns across multiple platforms (Rootly, PagerDuty, GitHub, Slack, Jira, Linear) to identify team members at risk of burnout. The system correlates user identities across platforms, collects activity data, and applies Copenhagen Burnout Inventory methodology to calculate risk scores. Now expanding to support token-based authentication for Jira and Linear to serve enterprise users blocked by OAuth security policies.

## Core Value

Catch exhaustion before it burns out team members by analyzing cross-platform activity patterns, on-call load, and workload distribution.

## Requirements

### Validated

<!-- Existing capabilities shipped and proven valuable -->

- ✓ OAuth-based authentication for user login (Google, GitHub) — existing
- ✓ OAuth integration setup for Jira and Linear (workspace/organization connection) — existing
- ✓ Encrypted token storage with automatic refresh for Jira OAuth tokens — existing (PR #291)
- ✓ Multi-platform user identity correlation and mapping — existing
- ✓ Burnout analysis engine with AI insights — existing
- ✓ Integration data collection from Rootly, PagerDuty, GitHub, Slack, Jira, Linear — existing
- ✓ Multi-tenant organization support (partially implemented) — existing
- ✓ Survey scheduling and delivery system — existing

### Active

<!-- Current scope for token-based authentication feature -->

- [ ] Token-based authentication option for Jira integration (alternative to OAuth)
- [ ] Token-based authentication option for Linear integration (alternative to OAuth)
- [ ] Integration setup UI shows both OAuth and Token options in modal
- [ ] Token validation during setup (verify token works)
- [ ] Encrypted token storage (same encryption as OAuth tokens)
- [ ] Token validity checking using existing mechanism
- [ ] Users can disconnect OAuth and reconnect with token
- [ ] Team-level data access with tokens (same as OAuth)

### Out of Scope

- Token-based auth for other integrations (GitHub, Slack, Rootly, PagerDuty) — only Jira and Linear for this feature
- Token permission verification (validating team-level access) — trust user knows token has right access
- Token rotation/expiry notifications — use existing token validation mechanism
- Migration from OAuth to token (automated) — users manually disconnect/reconnect if switching

## Context

**Why token-based auth:**
- Enterprise customers with security policies that block OAuth apps
- Users who need admin approval for OAuth but can generate personal API tokens themselves
- Simpler setup path for users who already have API tokens

**Current state:**
- Jira and Linear integrations use OAuth 2.0 with encrypted token storage
- Jira recently added automatic token refresh (PR #291)
- Linear uses OAuth with workspace mapping
- Token encryption uses `ENCRYPTION_KEY` environment variable with Fernet symmetric encryption
- Integration validator service checks token validity via API calls

**Technical environment:**
- Backend: FastAPI with SQLAlchemy ORM (Python 3.11+)
- Frontend: Next.js 16 with React 19, TypeScript, Tailwind CSS
- Database: PostgreSQL 15 with encrypted token storage
- Existing models: `JiraIntegration`, `LinearIntegration` with OAuth token fields

## Constraints

- **Encryption**: Token storage must use existing `ENCRYPTION_KEY` mechanism (Fernet) — consistency with OAuth tokens
- **Validation**: Token validation must use existing `IntegrationValidator` service patterns — reuse validation infrastructure
- **UI**: Modal design must follow existing integration setup patterns (Radix UI, shadcn components) — consistent UX
- **Compatibility**: Existing OAuth integrations must continue to work unchanged — no breaking changes
- **Team access**: Tokens must provide team-level visibility (not just user's own data) — same as OAuth

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Support tokens alongside OAuth (not replacement) | Users have different security contexts; some can't use OAuth, others prefer it | — Pending |
| Trust user for token permissions | No reliable way to test team-level access programmatically; user knows their org's token setup | — Pending |
| Validate token works, not permissions | API call to test connectivity is sufficient; team data access verified during actual sync | — Pending |
| Use same encryption as OAuth tokens | Consistency in security approach, leverage existing infrastructure | — Pending |
| Show both options in modal | Clear choice for users, discoverability of token option for blocked users | — Pending |

---
*Last updated: 2026-01-30 after initialization*
