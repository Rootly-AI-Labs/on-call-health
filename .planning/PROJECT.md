# API Key Management for On-Call Health

## What This Is

An API key management system for On-Call Health that replaces JWT tokens for programmatic access (MCP clients, integrations, automation). Users can create, manage, and revoke long-lived API keys with descriptive names, optional expiration dates, and usage tracking—without affecting their web session authentication.

## Core Value

MCP clients and automation tools can authenticate reliably without JWT token expiration or session coupling.

## Requirements

### Validated

- ✓ OAuth 2.0 authentication (Google, GitHub) for web login — existing
- ✓ JWT tokens for web session management (7-day expiry) — existing
- ✓ FastAPI backend with SQLAlchemy ORM and PostgreSQL — existing
- ✓ Next.js frontend with TypeScript and Tailwind CSS — existing
- ✓ User model with encrypted token storage — existing
- ✓ Rate limiting infrastructure (slowapi, Redis) — existing
- ✓ MCP server implementation with JWT auth — existing
- ✓ Security middleware with CSP and headers — existing

### Active

- [ ] API key model (user_id, name, key_hash, scope, created_at, last_used_at, expires_at)
- [ ] Generate API keys with prefix format (`och_live_...`)
- [ ] Hash API keys before storage (bcrypt or similar)
- [ ] Revoke API keys without affecting web session
- [ ] Display API key list with last 4 chars only (after creation)
- [ ] Show full key once on creation with copy-to-clipboard button
- [ ] Track last used timestamp per key
- [ ] Optional expiration date per key (user-configurable)
- [ ] Unlimited keys per user
- [ ] Rate limiting per API key (separate from user rate limit)
- [ ] Scoped permissions system (v1: "full_access" scope only)
- [ ] Dedicated "API Keys" navigation menu item
- [ ] API key creation UI with name and optional expiration
- [ ] API key list UI showing name, last 4 chars, created, last used, expires
- [ ] API key revocation UI (confirm dialog)
- [ ] Backend authentication middleware supporting both JWT and API keys
- [ ] MCP server updated to accept API keys instead of JWT
- [ ] Documentation for API key usage (curl examples, authentication headers)

### Out of Scope

- API management via REST API — UI only to prevent compromised key escalation
- IP address restrictions per key — can add later if needed
- Audit logging of key actions — can add later if needed
- Request count tracking per key — can add later if needed
- Test button in UI — documentation examples only
- Granular permission scopes (read-only, write-only, etc.) — v1 supports only "full_access", can add scopes in v2
- Auto-expiration after inactivity — only manual expiration dates supported

## Context

**Problem:**
- Current MCP authentication uses JWT tokens that expire after 7 days
- MCP clients break when tokens expire, requiring manual re-authentication
- Cannot revoke MCP access without invalidating web session
- No audit trail distinguishing MCP access from web UI access

**Technical Environment:**
- FastAPI backend with SQLAlchemy ORM
- Existing OAuth + JWT authentication system
- MCP server already implemented (`backend/app/mcp/server.py`)
- Rate limiting via Redis and slowapi
- Security middleware in place

**User Workflow:**
1. User navigates to "API Keys" menu item
2. Creates new key with descriptive name (e.g., "Claude Desktop")
3. Optionally sets expiration date
4. Sees full key once with copy button
5. Key displayed in list as `och_live_****1234` with metadata
6. Uses key in MCP client or automation scripts
7. Can revoke key anytime without affecting web login

## Constraints

- **Tech Stack**: Must use existing FastAPI + SQLAlchemy + PostgreSQL stack
- **Security**: API keys must be hashed before storage (never store plaintext)
- **Performance**: Key validation must be fast (<50ms) to not slow API requests
- **Compatibility**: Must work with existing JWT authentication (both auth methods supported)
- **Migration**: MCP server must continue supporting JWT during transition period

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Prefixed key format (`och_live_...`) | Easy to identify in logs, grep for leaked keys, clear in error messages | — Pending |
| Show full key once only | Industry standard (GitHub, Stripe), prevents key exposure if session compromised | — Pending |
| UI-only management (no REST API) | Prevents compromised key from creating/revoking other keys | — Pending |
| Rate limit per key | Prevents single compromised key from exhausting rate limit | — Pending |
| Scoped permissions v1 = full_access only | Ship faster, add granular scopes (read-only, etc.) in v2 | — Pending |
| Unlimited keys per user | User manages their own keys, no artificial limits | — Pending |
| Dedicated "API Keys" menu item | Not buried in Account Settings, signals developer feature | — Pending |
| Optional expiration dates | User can choose never-expire or set date, flexibility over forced expiration | — Pending |

---
*Last updated: 2026-01-30 after initialization*
