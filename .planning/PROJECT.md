# On-Call Health

## What This Is

On-Call Health is a burnout detection platform that analyzes on-call patterns across multiple platforms (Rootly, PagerDuty, GitHub, Slack, Jira, Linear) to identify team members at risk of burnout. The system correlates user identities across platforms, collects activity data, and applies Copenhagen Burnout Inventory methodology to calculate risk scores. Now expanding to support token-based authentication for Jira and Linear to serve enterprise users blocked by OAuth security policies.

## Core Value

Catch exhaustion before it burns out team members by analyzing cross-platform activity patterns, on-call load, and workload distribution.

## Current Milestone: v1.1 MCP Distribution

**Goal:** Enable zero-installation MCP server access via SSE-hosted endpoint and PyPI distribution, replacing direct database access with REST API calls.

**Target features:**
- SSE transport endpoint at `https://mcp.oncallhealth.com/sse` (or similar)
- REST API client layer (calls oncallhealth.ai APIs instead of direct DB)
- PyPI package `on-call-health-mcp` for self-hosted users
- Rate limiting and connection limits for hosted SSE
- Documentation for both deployment methods (SSE hosted + PyPI/uvx)

**Architecture shift:**
- **Before (v1.0)**: MCP server → stdio transport → direct database access
- **After (v1.1)**: MCP server → SSE/stdio transport → REST API calls → oncallhealth.ai

## Requirements

### Validated

<!-- Capabilities shipped and proven valuable -->

- ✓ OAuth-based authentication for user login (Google, GitHub)
- ✓ OAuth integration setup for Jira and Linear (workspace/organization connection)
- ✓ Encrypted token storage with automatic refresh for Jira OAuth tokens (PR #291)
- ✓ Multi-platform user identity correlation and mapping
- ✓ Burnout analysis engine with AI insights
- ✓ Integration data collection from Rootly, PagerDuty, GitHub, Slack, Jira, Linear
- ✓ Multi-tenant organization support (partially implemented)
- ✓ Survey scheduling and delivery system
- ✓ Token-based authentication for Jira integration (alternative to OAuth) — v1.1
- ✓ Token-based authentication for Linear integration (alternative to OAuth) — v1.1
- ✓ Integration setup UI with OAuth and Token options in modal — v1.1
- ✓ Token validation during setup (verify token works before save) — v1.1
- ✓ Encrypted token storage (same Fernet encryption as OAuth tokens) — v1.1
- ✓ Token validity checking with platform-specific error messages — v1.1
- ✓ Users can switch between OAuth and Token auth methods — v1.1
- ✓ Team-level data access with tokens (same as OAuth) — v1.1

### Active

<!-- No active requirements - ready for next milestone -->

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
| Support tokens alongside OAuth (not replacement) | Users have different security contexts; some can't use OAuth, others prefer it | ✓ Implemented v1.1 |
| Trust user for token permissions | No reliable way to test team-level access programmatically; user knows their org's token setup | ✓ Implemented v1.1 |
| Validate token works, not permissions | API call to test connectivity is sufficient; team data access verified during actual sync | ✓ Implemented v1.1 |
| Use same encryption as OAuth tokens | Consistency in security approach, leverage existing infrastructure | ✓ Implemented v1.1 |
| Show both options in modal | Clear choice for users, discoverability of token option for blocked users | ✓ Implemented v1.1 |

---
*Last updated: 2026-02-03 after v1.1 (Token Auth) completion and v1.2 (MCP Distribution) Phase 11 deployment*
