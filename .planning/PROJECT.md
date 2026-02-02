# API Key Management for On-Call Health

## What This Is

An API key management system for On-Call Health that enables programmatic access through long-lived API keys. Users can create, manage, and revoke API keys with descriptive names, optional expiration dates, and usage tracking—independent of their web session authentication.

## Core Value

MCP clients and automation tools can authenticate reliably without JWT token expiration or session coupling.

## Current State

**Version shipped:** v1.0 (2026-02-03)
**Status:** Production-ready MVP

**What's built:**
- Complete API key CRUD (create, list, revoke) via web UI
- Dual-hash authentication (SHA-256 + Argon2id) for <50ms validation
- Per-key rate limiting (100 req/min independent buckets)
- MCP server API key authentication (X-API-Key header)
- Frontend UI with masked display and one-time key reveal
- 31/31 requirements satisfied, 142 tests passing

**Tech stack:**
- Backend: FastAPI + SQLAlchemy + PostgreSQL + Redis
- Frontend: Next.js 16 + TypeScript + Tailwind CSS
- ~13k LOC added across 62 files

**Known limitations (tech debt):**
- MCP auth doesn't update last_used_at timestamp (low priority enhancement)
- CreateApiKeyResponse.last_four field unused in UI (cosmetic cleanup)

**See also:**
- Milestone archive: `.planning/milestones/v1.0-ROADMAP.md`
- Requirements archive: `.planning/milestones/v1.0-REQUIREMENTS.md`
- Audit report: `.planning/milestones/v1.0-MILESTONE-AUDIT.md`

## Requirements

### Validated

**Infrastructure (pre-existing):**
- ✓ OAuth 2.0 authentication (Google, GitHub) for web login — existing
- ✓ JWT tokens for web session management (7-day expiry) — existing
- ✓ FastAPI backend with SQLAlchemy ORM and PostgreSQL — existing
- ✓ Next.js frontend with TypeScript and Tailwind CSS — existing
- ✓ User model with encrypted token storage — existing
- ✓ Rate limiting infrastructure (slowapi, Redis) — existing
- ✓ MCP server implementation — existing
- ✓ Security middleware with CSP and headers — existing

**v1.0 MVP (shipped 2026-02-03):**
- ✓ API key model with dual-hash storage (SHA-256 + Argon2id) — v1.0
- ✓ Generate API keys with prefix format (`och_live_...`, 64 hex chars) — v1.0
- ✓ Revoke API keys without affecting web session (soft delete) — v1.0
- ✓ Display API key list with masked format (`och_live_...abcd`) — v1.0
- ✓ Show full key once on creation with copy-to-clipboard button — v1.0
- ✓ Track last used timestamp per key (async background update) — v1.0
- ✓ Optional expiration date per key (7d, 30d, 60d, 90d, custom, never) — v1.0
- ✓ Unlimited keys per user — v1.0
- ✓ Rate limiting per API key (100 req/min independent buckets) — v1.0
- ✓ Scoped permissions system (v1: "full_access" scope only) — v1.0
- ✓ Dedicated "API Keys" navigation menu item in user dropdown — v1.0
- ✓ API key creation UI with name and optional expiration — v1.0
- ✓ API key list UI (grid layout, all metadata, expiration badges) — v1.0
- ✓ API key revocation UI with confirmation dialog — v1.0
- ✓ Backend authentication middleware supporting both JWT and API keys — v1.0
- ✓ MCP server updated to accept API keys (X-API-Key header, rejects JWT) — v1.0
- ✓ Database indexes for fast validation (<50ms SHA-256 lookup) — v1.0
- ✓ Timing-safe comparison via Argon2 PasswordHasher — v1.0

### Active

(Next milestone requirements will be defined with `/gsd:new-milestone`)

### Out of Scope

- API management via REST API — UI only to prevent compromised key escalation
- IP address restrictions per key — high complexity, wait for demand
- Audit logging of key actions — can add when compliance requirements emerge
- Request count tracking per key — can add when usage insights requested
- Test button in UI — creates rate limit edge cases, documentation sufficient
- Granular permission scopes (read-only, write-only) — v1 supports only "full_access", can add scopes in v2
- Auto-expiration after inactivity — only manual expiration dates supported
- Email notifications for expiring keys — infrastructure complexity, spam concerns
- Automatic key rotation — breaks integrations silently
- Retrievable keys — security principle (never store plaintext)

## Context

**Problem:**
- Current MCP authentication uses JWT tokens that expire after 7 days
- MCP clients break when tokens expire, requiring manual re-authentication
- Cannot revoke MCP access without invalidating web session
- No audit trail distinguishing MCP access from web UI access

**Solution (shipped v1.0):**
- Long-lived API keys with optional expiration
- Independent revocation without affecting web session
- Per-key rate limiting and usage tracking
- Security: dual-hash storage, timing-safe comparison, one-time display

**Technical Environment:**
- FastAPI backend with SQLAlchemy ORM and PostgreSQL
- OAuth 2.0 + JWT authentication for web (unchanged)
- MCP server at `backend/app/mcp/server.py` (updated for API keys)
- Rate limiting via Redis and slowapi
- Security middleware with CSP and headers

**User Workflow:**
1. User navigates to "API Keys" menu item in dropdown
2. Creates new key with descriptive name (e.g., "Claude Desktop")
3. Optionally sets expiration date (presets or custom)
4. Sees full key once with copy button and security warning
5. Key displayed in list as `och_live_...abcd` with metadata
6. Uses key in MCP client via X-API-Key header
7. Can revoke key anytime without affecting web login

## Constraints

- **Tech Stack**: Must use existing FastAPI + SQLAlchemy + PostgreSQL stack ✓
- **Security**: API keys must be hashed before storage (never store plaintext) ✓
- **Performance**: Key validation must be fast (<50ms) to not slow API requests ✓ (achieved ~45ms)
- **Compatibility**: Must work with existing JWT authentication (both auth methods supported) ✓
- **Migration**: MCP server continues supporting JWT during transition (not enforced - API keys preferred)

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Prefixed key format (`och_live_...`) | Easy to identify in logs, grep for leaked keys, clear in error messages | ✓ Good - Implemented |
| Show full key once only | Industry standard (GitHub, Stripe), prevents key exposure if session compromised | ✓ Good - Strong security warning in UI |
| UI-only management (no REST API) | Prevents compromised key from creating/revoking other keys | ✓ Good - JWT-only endpoints |
| Rate limit per key | Prevents single compromised key from exhausting rate limit | ✓ Good - Independent buckets |
| Scoped permissions v1 = full_access only | Ship faster, add granular scopes (read-only, etc.) in v2 | ✓ Good - Simplified v1 |
| Unlimited keys per user | User manages their own keys, no artificial limits | ✓ Good - No complaints |
| Dedicated "API Keys" menu item | Not buried in Account Settings, signals developer feature | ✓ Good - Easy to find |
| Optional expiration dates | User can choose never-expire or set date, flexibility over forced expiration | ✓ Good - GitHub-style presets |
| Dual-hash pattern (SHA-256 + Argon2id) | Fast lookup without compromising security | ✓ Good - <50ms target met |
| JWT-only for web, API-key-only for MCP | Clean separation prevents auth confusion | ✓ Good - Clear boundaries |
| Soft delete with revoked_at | Audit trail and potential recovery | ✓ Good - No issues |
| Frontend masked_key format | Backend returns full masked format for consistency | ✓ Good - Fixed initial type mismatch |

---

*Last updated: 2026-02-03 after v1.0 milestone completion*
