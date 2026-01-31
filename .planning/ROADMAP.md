# Roadmap: API Key Management

**Project:** API Key Management for On-Call Health
**Milestone:** v1.0 - MVP Launch
**Created:** 2026-01-30
**Status:** Active

## Overview

This roadmap breaks down the API Key Management v1.0 implementation into 4 sequential phases based on architectural dependencies. Each phase builds on the previous, ensuring working software at every checkpoint.

**Total Requirements:** 31 (21 functional, 10 non-functional)
**Estimated Phases:** 4
**Build Order:** Model -> Auth -> API -> UI

## Phase Architecture

```
Phase 1: Database Model & Core Logic
    └─> Phase 2: Authentication Middleware Integration
            └─> Phase 3: API Endpoints
                    └─> Phase 4: Frontend UI & UX
```

**Dependency Rationale:**
- Can't authenticate without model to store keys (Phase 1 -> 2)
- Can't build endpoints without auth middleware (Phase 2 -> 3)
- Can't build UI without API endpoints (Phase 3 -> 4)
- Each phase is independently testable

---

## Phase 1: Database Model & Core Logic

**Goal:** Create APIKey model with hashing, validation, and database schema

**Phase Requirements:** 11 requirements

**Plans:** 3 plans

Plans:
- [x] 01-01-PLAN.md - Add argon2-cffi dependency, create APIKey model, update exports
- [x] 01-02-PLAN.md - Create API key service with dual-hash generation and SQL migration
- [x] 01-03-PLAN.md - Unit tests for model and service functions

### Functional Requirements
- REQ-F-001: API Key Creation (data model)
- REQ-F-002: Prefixed Key Format
- REQ-F-007: Optional Expiration Date
- REQ-F-008: Unlimited Keys Per User
- REQ-F-011: Created Timestamp
- REQ-F-012: Last Used Timestamp
- REQ-F-013: Hashed Storage (dual-hash)
- REQ-F-017: Full Access Scope Only (v1)

### Non-Functional Requirements
- REQ-NF-002: Database Indexing
- REQ-NF-005: Cryptographically Secure Random
- REQ-NF-006: No Plaintext Storage
- REQ-NF-008: Existing Stack Compatibility

### Success Criteria
- [x] APIKey SQLAlchemy model created with all fields
- [x] Database migration generated and tested
- [x] Indexes created on `key_hash`, `user_id`, `last_used_at`
- [x] Key generation function using `secrets.token_hex(32)`
- [x] Dual-hash implementation (SHA-256 + Argon2id)
- [x] Model unit tests pass (creation, hashing, validation)
- [x] Foreign key relationship to User model established

### Key Files
**Backend:**
- `backend/app/models/api_key.py` - SQLAlchemy model
- `backend/migrations/2026_01_30_add_api_keys.sql` - Migration
- `backend/app/services/api_key_service.py` - Business logic
- `backend/tests/test_api_key_model.py` - Unit tests

**Database Schema:**
```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash_sha256 VARCHAR(64) NOT NULL,  -- Fast indexed lookup
    key_hash_argon2 TEXT NOT NULL,          -- Cryptographic verification
    prefix VARCHAR(20) NOT NULL DEFAULT 'och_live_',
    last_four VARCHAR(4) NOT NULL,
    scope VARCHAR(50) NOT NULL DEFAULT 'full_access',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,

    INDEX idx_api_keys_key_hash_sha256 (key_hash_sha256),
    INDEX idx_api_keys_user_id (user_id),
    INDEX idx_api_keys_last_used_at (last_used_at),
    UNIQUE (user_id, name)
);
```

### Technical Notes
- Use `argon2-cffi` version 25.1.0 (NOT passlib - unmaintained)
- Dual-hash pattern: SHA-256 for fast lookup, Argon2id for verification
- Store `last_four` separately for masked display (never compute from hash)
- Soft delete pattern: `revoked_at` timestamp instead of hard delete
- Use Integer primary keys to match existing codebase pattern (not UUID)

### Dependencies
- Existing: User model, database connection, SQL migrations
- New: `argon2-cffi==25.1.0` package

### Risks & Mitigations
- **Risk:** Wrong hashing algorithm slows auth flow
  - **Mitigation:** Use dual-hash pattern as researched, benchmark validation <50ms
- **Risk:** Missing indexes cause 35x slowdown
  - **Mitigation:** Create all indexes in migration, verify with EXPLAIN ANALYZE

---

## Phase 2: Authentication Middleware Integration

**Goal:** Extend authentication to support both JWT and API keys with unified dependency

**Phase Requirements:** 6 requirements

**Plans:** 4 plans

Plans:
- [x] 02-01-PLAN.md - Create FastAPI API key authentication dependency with two-phase validation
- [x] 02-02-PLAN.md - Update MCP auth for API key support (reject JWT, accept X-API-Key)
- [x] 02-03-PLAN.md - Extend rate limiting for per-key rate limits (100 req/min per key)
- [x] 02-04-PLAN.md - Unit tests for API key auth (FastAPI and MCP)

### Functional Requirements
- REQ-F-005: Key Revocation (validation logic)
- REQ-F-014: Dual Authentication Support
- REQ-F-015: Per-Key Rate Limiting
- REQ-F-016: HTTPS Transmission Only

### Non-Functional Requirements
- REQ-NF-001: Fast Key Validation (<50ms)
- REQ-NF-003: Async Last Used Update
- REQ-NF-004: Timing-Safe Comparison
- REQ-NF-007: Backward Compatibility with JWT
- REQ-NF-009: Structured Logging
- REQ-NF-010: Error Messages

### Success Criteria
- [x] Separate auth dependencies: `get_current_user` for JWT (web), `get_current_user_from_api_key` for API keys (MCP)
- [x] MCP endpoints use API key auth only (reject JWT per CONTEXT.md decision)
- [x] API key validation <50ms (p95) in benchmarks
- [x] Revoked keys rejected with clear error message
- [x] Expired keys rejected with expiration date in error
- [x] Last used timestamp updates asynchronously
- [x] Per-key rate limiting using Redis
- [x] All existing JWT tests still pass (no breaking changes)
- [x] MCP server works with API keys
- [x] Integration tests for both auth methods pass

### Key Files
**Backend:**
- `backend/app/auth/api_key_auth.py` - API key FastAPI dependency (NEW)
- `backend/app/mcp/auth.py` - MCP auth updated for API keys (MODIFY)
- `backend/app/mcp/server.py` - MCP tool handlers wired to API key auth (MODIFY)
- `backend/app/core/rate_limiting.py` - Per-key rate limiter (MODIFY)
- `backend/tests/test_api_key_auth.py` - FastAPI API key auth tests (NEW)
- `backend/tests/test_mcp_api_key_auth.py` - MCP API key auth tests (NEW)

### Authentication Architecture
Per CONTEXT.md decision, authentication is cleanly separated by use case:

**Web Endpoints (JWT-only):**
- Use existing `get_current_user` dependency
- Checks Authorization header (Bearer JWT) and httpOnly cookies
- No API key support - web endpoints remain unchanged

**MCP Endpoints (API-key-only):**
- Use new `get_current_user_from_api_key` dependency (FastAPI)
- Use new `require_user_api_key` function (MCP context)
- Checks X-API-Key header
- Rejects JWT tokens with helpful error message

### Technical Notes
- Use `hmac.compare_digest()` for timing-safe hash comparison
- SHA-256 hash indexed lookup first, then Argon2id verification
- Update `last_used_at` in background task (fire-and-forget)
- Rate limiting key format: `api_key_ratelimit:{key_id}`
- Existing JWT rate limiting unchanged

### Dependencies
- Phase 1 complete: APIKey model exists and is queryable
- Existing: Redis connection, slowapi rate limiter

### Risks & Mitigations
- **Risk:** Auth precedence confusion breaks JWT users
  - **Mitigation:** JWT checked first, extensive compatibility tests
- **Risk:** Timing attacks leak key existence
  - **Mitigation:** Use `hmac.compare_digest()`, log generic "invalid key" only
- **Risk:** Last used update adds latency
  - **Mitigation:** Async update in background task, benchmark confirms <10ms impact

---

## Phase 3: API Endpoints

**Goal:** Create REST API endpoints for key CRUD operations (UI-only, no programmatic access)

**Phase Requirements:** 6 requirements

**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md - Implement API key CRUD endpoints (create, list, revoke) with JWT auth
- [x] 03-02-PLAN.md - Integration tests for API key endpoints

### Functional Requirements
- REQ-F-001: API Key Creation (endpoint)
- REQ-F-003: Show Full Key Once
- REQ-F-004: Copy-to-Clipboard (backend support)
- REQ-F-005: Key Revocation (endpoint)
- REQ-F-006: Revocation Confirmation Dialog (backend support)
- REQ-F-009: Key List View (endpoint)
- REQ-F-010: Masked Key Display (endpoint)

### Non-Functional Requirements
(Already satisfied by Phase 2, testing in this phase)

### Success Criteria
- [x] `POST /api-keys` - Create key with name and optional expiration
- [x] `GET /api-keys` - List all keys for authenticated user (masked)
- [x] `DELETE /api-keys/{key_id}` - Revoke key with soft delete
- [x] All endpoints require JWT authentication (not API key auth - prevent escalation)
- [x] Created key response includes full key value (once only)
- [x] List response includes: id, name, last_four, created_at, last_used_at, expires_at
- [x] Revoked keys excluded from list response
- [x] OpenAPI schema updated
- [x] Endpoint integration tests pass
- [x] Rate limiting applied to endpoints

### Key Files
**Backend:**
- `backend/app/api/endpoints/api_keys.py` - CRUD endpoints (NEW)
- `backend/app/main.py` - Router registration (MODIFY)
- `backend/app/services/api_key_service.py` - Business logic (existing)
- `backend/tests/test_api_keys_endpoints.py` - Endpoint tests (NEW)

### API Specification

**POST /api-keys**
```json
Request:
{
  "name": "Claude Desktop",
  "expires_at": "2026-03-30T00:00:00Z"  // optional
}

Response: 201 Created
{
  "id": "uuid",
  "name": "Claude Desktop",
  "key": "och_live_a1b2c3...",  // FULL KEY - shown once only
  "last_four": "xyz9",
  "created_at": "2026-01-30T12:00:00Z",
  "expires_at": "2026-03-30T00:00:00Z"
}
```

**GET /api-keys**
```json
Response: 200 OK
{
  "keys": [
    {
      "id": "uuid",
      "name": "Claude Desktop",
      "last_four": "xyz9",
      "created_at": "2026-01-30T12:00:00Z",
      "last_used_at": "2026-01-30T14:30:00Z",
      "expires_at": null
    }
  ]
}
```

**DELETE /api-keys/{key_id}**
```json
Response: 204 No Content
```

### Technical Notes
- Endpoints ONLY accessible via JWT (not API key) to prevent escalation
- Use existing `get_current_active_user` dependency for JWT auth
- Revocation sets `revoked_at` timestamp (soft delete)
- List endpoint filters out revoked keys (`WHERE revoked_at IS NULL`)
- Rate limit: 10 creates/min, 100 lists/min, 10 deletes/min

### Dependencies
- Phase 2 complete: Auth middleware supports API keys
- Existing: FastAPI router infrastructure, Pydantic models

### Risks & Mitigations
- **Risk:** API key can manage other API keys (escalation attack)
  - **Mitigation:** Endpoints require JWT only, not API key auth
- **Risk:** Full key accidentally logged
  - **Mitigation:** Never log key value, only key_id

---

## Phase 4: Frontend UI & UX

**Goal:** Build user-facing interface for API key management

**Phase Requirements:** 8 requirements

### Functional Requirements
- REQ-F-003: Show Full Key Once (UI)
- REQ-F-004: Copy-to-Clipboard (UI button)
- REQ-F-006: Revocation Confirmation Dialog (UI)
- REQ-F-007: Optional Expiration Date (UI form)
- REQ-F-009: Key List View (UI table)
- REQ-F-010: Masked Key Display (UI)
- REQ-F-018: Dedicated API Keys Navigation
- REQ-F-019: Key Creation UI
- REQ-F-020: Key List UI
- REQ-F-021: Key Revocation UI

### Non-Functional Requirements
(Already satisfied by previous phases)

### Success Criteria
- [ ] "API Keys" menu item in user dropdown navigation
- [ ] API Keys page at `/dashboard/api-keys` route
- [ ] Empty state: "No API keys yet. Create your first key to get started."
- [ ] "Create API Key" button opens modal
- [ ] Creation modal: name field (required), expiration dropdown
- [ ] Success modal shows full key with monospace font
- [ ] Copy button with "Copied!" visual feedback
- [ ] Warning: "This is the only time you'll see this key"
- [ ] Key list table with all metadata columns
- [ ] "Revoke" button per key with confirmation dialog
- [ ] Mobile-responsive design
- [ ] Loading states for async operations
- [ ] Error handling with user-friendly messages
- [ ] Success/error toast notifications

### Key Files
**Frontend:**
- `frontend/src/app/dashboard/api-keys/page.tsx` - Main page (NEW)
- `frontend/src/components/ApiKeyCreateModal.tsx` - Creation modal (NEW)
- `frontend/src/components/ApiKeySuccessModal.tsx` - Show-once modal (NEW)
- `frontend/src/components/ApiKeyList.tsx` - List table (NEW)
- `frontend/src/components/ApiKeyRevokeDialog.tsx` - Confirm dialog (NEW)
- `frontend/src/hooks/useApiKeys.ts` - Data fetching hook (NEW)
- `frontend/src/types/apiKey.ts` - TypeScript types (NEW)
- `frontend/src/app/dashboard/layout.tsx` - Add navigation link (MODIFY)

### UI Components

**API Keys Page (`/dashboard/api-keys`):**
- Header: "API Keys" with description
- "Create API Key" button (top right)
- Key list table (or empty state)
- Footer: Link to documentation

**Create Modal:**
- Title: "Create API Key"
- Name input (required, placeholder: "Claude Desktop")
- Expiration dropdown: Never, 30 days, 90 days, 1 year, Custom
- Custom date picker (if Custom selected)
- Cancel / Create buttons

**Success Modal:**
- Title: "API Key Created"
- Full key in monospace code block
- Copy button with icon
- Warning banner: "Save this key now. You won't be able to see it again."
- "Done" button (primary action)

**Key List Table:**
| Name | Key | Created | Last Used | Expires | Actions |
|------|-----|---------|-----------|---------|---------|
| Claude Desktop | `och_live_****xyz9` | Jan 30, 2026 | 2 hours ago | Never | Revoke |

**Revoke Confirmation Dialog:**
- Title: "Revoke API Key?"
- Body: "This will permanently revoke '{key_name}'. Any applications using this key will stop working immediately."
- Cancel (secondary) / Revoke (danger red) buttons

### Technical Notes
- Use Next.js 16 App Router conventions
- TypeScript for all components
- Tailwind CSS for styling (match existing design system)
- Use existing UI component library (buttons, modals, tables)
- Client-side copy to clipboard: `navigator.clipboard.writeText()`
- React state management: useState for modals, SWR for data fetching
- Optimistic UI updates for revocation

### Dependencies
- Phase 3 complete: API endpoints functional and tested
- Existing: Next.js routing, UI component library, auth context

### Risks & Mitigations
- **Risk:** User closes success modal before copying key
  - **Mitigation:** Require explicit "Done" click, not auto-close
- **Risk:** User accidentally revokes active key
  - **Mitigation:** Confirmation dialog with key name shown, danger styling

---

## Phase Summary

| Phase | Requirements | Estimated Effort | Critical Path |
|-------|--------------|------------------|---------------|
| Phase 1: Database Model | 11 | Medium | Yes |
| Phase 2: Auth Middleware | 6 | High | Yes |
| Phase 3: API Endpoints | 6 | Low | Yes |
| Phase 4: Frontend UI | 8 | Medium | Yes |

**Total:** 31 requirements across 4 phases

## Success Metrics

### Phase Completion Criteria
Each phase must satisfy:
- [ ] All phase requirements implemented
- [ ] All success criteria checked off
- [ ] Unit tests pass for new code
- [ ] Integration tests pass for phase scope
- [ ] No regressions in existing functionality
- [ ] Code reviewed (if team review process)
- [ ] Committed with descriptive message
- [ ] Phase documented in STATE.md

### v1.0 Launch Criteria
Before declaring v1.0 complete:
- [ ] All 4 phases complete
- [ ] End-to-end test: Create key via UI -> Use key in MCP -> Revoke key
- [ ] Performance benchmarks met (<50ms auth, <500ms UI operations)
- [ ] Security checklist completed (timing attacks, indexing, no plaintext)
- [ ] Documentation written (API usage, curl examples)
- [ ] MCP server updated to prefer API keys in examples
- [ ] Existing JWT users unaffected (backward compatibility verified)
- [ ] Deployed to staging environment and tested
- [ ] User acceptance testing completed

## Post-v1.0 Roadmap

### v1.1 Features (Quick Wins)
- Dashboard warning banner for expiring keys (7 days before expiration)
- Request count tracking per key
- Audit logging of key lifecycle events

### v2.0 Features (Future Enhancements)
- Scoped permissions (read-only, write-only, admin)
- IP allowlisting per key
- Key usage analytics dashboard
- Team/organization key sharing

### Deferred Indefinitely
- REST API for key management (security tradeoff)
- Retrievable keys (security principle)
- Automatic key rotation (breaks integrations)
- Test button in UI (documentation sufficient)

---

## Dependencies Graph

```
User Model (existing)
    └─> Phase 1: APIKey Model
            ├─> Phase 2: Auth Middleware
            │       ├─> Phase 3: API Endpoints
            │       │       └─> Phase 4: Frontend UI
            │       └─> MCP Server (updated transparently)
            └─> Redis (existing, extended for per-key rate limits)

JWT Auth (existing)
    └─> Phase 2: Unified Auth Dependency
            └─> Backward compatibility maintained
```

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Wrong hashing slows auth | Medium | High | Dual-hash pattern, benchmark | Phase 2 |
| Missing indexes degrade perf | Medium | High | Create all indexes in Phase 1 | Phase 1 |
| Timing attacks leak keys | Low | Critical | Use hmac.compare_digest() | Phase 2 |
| JWT compatibility broken | Low | Critical | Extensive compatibility tests | Phase 2 |
| User loses key before copying | Medium | Medium | Require explicit "Done" click | Phase 4 |
| API key can manage keys | Low | Critical | JWT-only endpoints | Phase 3 |

---

*Created: 2026-01-30*
*Status: Active - Phase 3 planning complete*
*Next: Execute Phase 3*
