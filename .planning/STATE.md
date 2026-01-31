# Project State: API Key Management

**Project:** API Key Management for On-Call Health
**Milestone:** v1.0 - MVP Launch
**Updated:** 2026-01-31
**Status:** 🟢 Phase 3 Complete

## Current State

### Progress Overview

```
Phase 1: Database Model   [████████████████████]  100%  (4/4 plans)
Phase 2: Auth Middleware  [████████████████████]  100%  (4/4 plans)
Phase 3: API Endpoints    [████████████████████]  100%  (2/2 plans)
Phase 4: Frontend UI      [░░░░░░░░░░░░░░░░░░░░]   0%
```

**Overall Project Progress:** 10/12 plans completed (83%)

### Active Phase

**Current:** Phase 3 - API Endpoints COMPLETE
**Plan:** 03-02-PLAN.md COMPLETE
**Next:** Phase 4 - Frontend UI
**Blocking:** None

### Phase Status

| Phase | Status | Plans | Completed | Progress |
|-------|--------|-------|-----------|----------|
| Phase 1: Database Model | 🟢 Complete | 4 | 4/4 | 100% |
| Phase 2: Auth Middleware | 🟢 Complete | 4 | 4/4 | 100% |
| Phase 3: API Endpoints | 🟢 Complete | 2 | 2/2 | 100% |
| Phase 4: Frontend UI | 🔵 Not Started | TBD | 0/TBD | 0% |

**Status Legend:**
- 🔵 Not Started
- 🟡 In Progress
- 🟢 Complete
- 🔴 Blocked

---

## Recent Activity

### 2026-01-31 - Phase 3 Verified

**Phase Verification:**
- Status: PASSED (12/12 must-haves verified)
- All endpoints verified against must_haves from plans
- All tests passing (98 total API key tests)
- VERIFICATION.md created with detailed report
- Ready for Phase 4

### 2026-01-31 - Plan 03-02 Complete

**Actions Taken:**
1. Created test_api_keys_endpoints.py with 21 integration tests
2. Covered all 3 endpoints (POST, GET, DELETE) with TestClient
3. Tests verify JWT authentication required (401 without token)
4. Tests verify Pydantic validation errors (422 for invalid input)
5. Tests verify business logic errors (400, 404)
6. Tests verify success responses (201, 200, 204)
7. All 549 tests pass with no regressions

**Commits:**
- `05eb27e4` - test(03-02): integration tests for API key endpoints

**Files Created:**
- `backend/tests/test_api_keys_endpoints.py` - Integration tests (386 lines, 21 tests)

**Test Totals:**
- test_api_key_model.py: 36 tests
- test_api_key_auth.py: 18 tests
- test_mcp_api_key_auth.py: 23 tests
- test_api_keys_endpoints.py: 21 tests
- **Total API key tests: 98**

### 2026-01-30 - Plan 03-01 Complete

**Actions Taken:**
1. Created api_keys.py with POST, GET, DELETE endpoints
2. Implemented JWT-only authentication via get_current_active_user
3. Applied rate limiting decorators (integration_create, integration_get, integration_update)
4. Added Pydantic v2 validators for name and expires_at fields
5. Registered router in main.py with prefix="/api"
6. All 528 existing tests pass with no regressions

**Commits:**
- `eba598e3` - feat(03-01): create API key CRUD endpoints
- `7ff3f8a9` - feat(03-01): register API key router in main.py

**Files Created:**
- `backend/app/api/endpoints/api_keys.py` - API key CRUD endpoints (152 lines)

**Files Modified:**
- `backend/app/main.py` - Added api_keys router registration

### 2026-01-31 - Plan 02-04 Complete

**Actions Taken:**
1. Created test_api_key_auth.py with 18 unit tests for FastAPI API key auth dependency
2. Created test_mcp_api_key_auth.py with 23 unit tests for MCP API key authentication
3. Updated test_mcp_server.py to mock require_user_api_key instead of require_user
4. All 99 API key related tests pass

**Commits:**
- `31a8383f` - test(02-04): add unit tests for FastAPI API key auth dependency
- `125529eb` - test(02-04): add unit tests for MCP API key authentication
- `4739dc28` - refactor(02-04): update MCP server tests for API key authentication

**Files Created:**
- `backend/tests/test_api_key_auth.py` - FastAPI auth dependency tests (566 lines, 18 tests)
- `backend/tests/test_mcp_api_key_auth.py` - MCP auth tests (376 lines, 23 tests)

**Files Modified:**
- `backend/tests/test_mcp_server.py` - Updated 9 tests to mock require_user_api_key

### 2026-01-31 - Plan 02-03 Complete

**Actions Taken:**
1. Added "api_key_mcp": "100/minute" rate limit to RATE_LIMITS dict
2. Extended get_rate_limit_key to check request.state.api_key_id first (Priority 1)
3. Returns "api_key:{id}" format for per-key rate limiting
4. Added mcp_rate_limit() decorator function following existing pattern
5. Existing JWT and IP-based rate limiting unchanged

**Commits:**
- `917288cf` - feat(02-03): add api_key_mcp rate limit configuration
- `27cd7d79` - feat(02-03): extend get_rate_limit_key for API key detection
- `137ea0df` - feat(02-03): add mcp_rate_limit decorator function

**Files Modified:**
- `backend/app/core/rate_limiting.py` - Extended with per-API-key rate limiting

### 2026-01-31 - Plan 02-02 Complete

**Actions Taken:**
1. Added `extract_api_key_header` function to extract X-API-Key from MCP context
2. Added `require_user_api_key` function with two-phase validation (SHA-256 + Argon2)
3. JWT tokens rejected with helpful error message guiding to X-API-Key
4. Wired all 5 MCP tool handlers to use require_user_api_key
5. Preserved require_user function for backward compatibility

**Commits:**
- `7d890aa7` - feat(02-02): add extract_api_key_header function for MCP context
- `0894b08a` - feat(02-02): add require_user_api_key function for MCP authentication
- `28543ed2` - feat(02-02): wire MCP tool handlers to API key authentication

**Files Modified:**
- `backend/app/mcp/auth.py` - Added extract_api_key_header and require_user_api_key (+95 lines)
- `backend/app/mcp/server.py` - Updated all 5 tool handlers to use require_user_api_key

### 2026-01-31 - Plan 02-01 Complete

**Actions Taken:**
1. Created `api_key_auth.py` with FastAPI dependency for API key authentication
2. Implemented two-phase validation (SHA-256 lookup + Argon2 verification)
3. Argon2 runs in asyncio.to_thread to avoid blocking event loop
4. Specific error messages for revoked and expired keys
5. JWT rejection returns 400 with helpful message
6. Background task updates last_used_at without blocking response
7. Stored api_key_id in request.state for rate limiting

**Commits:**
- `22e460a6` - feat(02-01): create API key authentication dependency

**Files Created:**
- `backend/app/auth/api_key_auth.py` - API key authentication dependency (174 lines)

### 2026-01-30 - Plan 01-03 Complete

**Actions Taken:**
1. Created comprehensive unit test file with 36 test functions
2. Covered key generation (prefix, length, entropy, hash matching)
3. Covered key verification (correct/wrong key, empty string, malformed hash)
4. Covered SHA-256 hashing (determinism, hex format, uniqueness)
5. Covered APIKey model properties (is_active, masked_key, to_dict, __repr__)
6. Verified all tests pass without database dependency

**Commits:**
- `3afe16e6` - test(01-03): add comprehensive unit tests for API key model and service

**Files Created:**
- `backend/tests/test_api_key_model.py` - Unit tests (404 lines, 36 tests)

### 2026-01-30 - Plan 01-02 Complete

**Actions Taken:**
1. Created api_key_service.py with generate_api_key(), verify_api_key(), compute_sha256_hash()
2. Created APIKeyService class with create_key, list_user_keys, revoke_key, find_by_sha256_hash
3. Created SQL migration with CREATE TABLE (12 columns) and 4 indexes
4. Verified key generation produces och_live_ prefix + 64 hex characters
5. Verified Argon2id verification works correctly

**Commits:**
- `cc95cc86` - feat(01-02): create API key service with generation and verification
- `51c7b595` - feat(01-02): create SQL migration for api_keys table

**Files Created:**
- `backend/app/services/api_key_service.py` - API key service (199 lines)
- `backend/migrations/2026_01_30_add_api_keys.sql` - Database migration (68 lines)

### 2026-01-30 - Plan 01-01 Complete

**Actions Taken:**
1. Added argon2-cffi==25.1.0 to requirements.txt
2. Created APIKey SQLAlchemy model with dual-hash storage
3. Added User.api_keys bidirectional relationship
4. Exported APIKey from models package

**Commits:**
- `6a2022c1` - chore(01-01): add argon2-cffi dependency
- `2c331aad` - feat(01-01): create APIKey model with dual-hash storage
- `63fe3d0f` - feat(01-01): export APIKey and add User.api_keys relationship

**Files Created:**
- `backend/app/models/api_key.py` - APIKey model (121 lines)

**Files Modified:**
- `backend/requirements.txt` - Added argon2-cffi
- `backend/app/models/__init__.py` - Export APIKey
- `backend/app/models/user.py` - Add api_keys relationship

### 2026-01-30 - Project Initialization

**Actions Taken:**
1. Created PROJECT.md with validated and active requirements
2. Created config.json with workflow settings (quality model profile)
3. Fixed .gitignore to allow planning docs to be committed
4. Spawned 4 parallel Opus research agents (stack, features, architecture, pitfalls)
5. Synthesized research into SUMMARY.md with high confidence
6. Generated REQUIREMENTS.md with 31 requirements (21 functional, 10 non-functional)
7. Created ROADMAP.md with 4-phase breakdown
8. Initialized STATE.md (this file)

---

## Accumulated Decisions

| Decision | Rationale | Made In |
|----------|-----------|---------|
| Dual-hash pattern (SHA-256 + Argon2id) | <50ms validation with cryptographic security | Research |
| Integer primary keys | Match codebase pattern | 01-01 |
| `och_live_` prefix | Industry convention (like Stripe sk_live_) | 01-01 |
| `full_access` scope default | v1 simplicity, granular later | 01-01 |
| Cascade delete on api_keys | Clean up keys when user deleted | 01-01 |
| argon2-cffi (not passlib) | passlib unmaintained since 2020 | Research |
| UI-only key management | Prevent compromised key escalation | Research |
| secrets.token_hex(32) for entropy | 256 bits cryptographically secure | 01-02 |
| Module-level PasswordHasher | Thread-safe, reusable instance | 01-02 |
| Partial unique index on (user_id, name) | Allow name reuse after revocation | 01-02 |
| Pytest class-based test organization | Matches existing test patterns | 01-03 |
| Direct model instantiation for tests | No database dependency needed | 01-03 |
| JWT rejection returns 400 (not 401) | Clear auth method separation | 02-01 |
| request.state for api_key_id | Pass auth context to rate limiting | 02-01 |
| Raw SQL UPDATE for last_used_at | Efficiency over ORM pattern | 02-01 |
| New session in background task | Thread safety for BackgroundTasks | 02-01 |
| API key ID highest priority in rate limit key | Each key gets independent bucket | 02-03 |
| Independent buckets per key | Different keys for same user get separate limits | 02-03 |
| MCP endpoints API-key-only | Per CONTEXT.md, JWT rejected with guidance | 02-02 |
| require_user preserved | Backward compatibility for non-MCP uses | 02-02 |
| Sync Argon2 in MCP | MCP handlers are async but verify_api_key is sync-safe | 02-02 |
| Mock database in unit tests | Avoid test database dependency | 02-04 |
| Test all error paths | Comprehensive edge case coverage | 02-04 |
| Rate limiter Request parameter | slowapi requires explicit request: Request param | 03-01 |
| Pydantic body param naming | Use 'body' not 'request' to avoid FastAPI Request collision | 03-01 |
| TestClient with dependency overrides | FastAPI's recommended integration test pattern | 03-02 |
| Router prefix alignment | Mount at /api to match main.py and avoid path doubling | 03-02 |

---

## Known Issues

None

---

## Technical Debt

None - greenfield feature

---

## Dependencies

### External Dependencies
**Added:**
- `argon2-cffi==25.1.0` - Argon2id hashing (ADDED in 01-01)

**Existing (Already Available):**
- FastAPI, SQLAlchemy, PostgreSQL, Redis, slowapi
- Next.js 16, TypeScript, Tailwind CSS

### Internal Dependencies
**Modified:**
- `backend/app/models/user.py` - Added api_keys relationship (01-01)
- `backend/app/models/__init__.py` - Export APIKey (01-01)
- `backend/app/mcp/auth.py` - Added API key auth for MCP (02-02)
- `backend/app/mcp/server.py` - Wired to API key auth (02-02)
- `backend/app/core/rate_limiting.py` - Per-key rate limiting (02-03)
- `backend/tests/test_mcp_server.py` - Updated to mock require_user_api_key (02-04)
- `backend/app/main.py` - Added api_keys router registration (03-01)

**Created:**
- `backend/app/models/api_key.py` - APIKey model (01-01)
- `backend/app/services/api_key_service.py` - API key generation/verification (01-02)
- `backend/migrations/2026_01_30_add_api_keys.sql` - Database migration (01-02)
- `backend/tests/test_api_key_model.py` - Unit tests (01-03)
- `backend/app/auth/api_key_auth.py` - API key authentication dependency (02-01)
- `backend/tests/test_api_key_auth.py` - FastAPI auth dependency tests (02-04)
- `backend/tests/test_mcp_api_key_auth.py` - MCP auth tests (02-04)
- `backend/app/api/endpoints/api_keys.py` - API key CRUD endpoints (03-01)
- `backend/tests/test_api_keys_endpoints.py` - Endpoint integration tests (03-02)

---

## Next Actions

### Immediate (Next Phase)
1. Execute Phase 4 - Frontend UI

### Upcoming Phases
- Phase 4: Frontend UI components and routing
  - API key management page
  - Create/revoke UI flows
  - Settings integration

---

## Session Continuity

**Last session:** 2026-01-31T02:03:00Z
**Stopped at:** Completed 03-02-PLAN.md (Phase 3 Complete)
**Resume file:** None - ready for Phase 4 execution

---

*Last Updated: 2026-01-31*
*Next Update: After Phase 4 planning/execution*
