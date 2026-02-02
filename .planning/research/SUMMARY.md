# Project Research Summary

**Project:** API Key Management for On-Call Health
**Domain:** Authentication & Authorization (API Key System)
**Researched:** 2026-01-30
**Confidence:** HIGH

## Executive Summary

This research synthesizes findings from deep investigation into building API key management for the existing On-Call Health FastAPI application. The goal is to enable MCP clients (Claude Desktop) and automation tools to authenticate without relying on short-lived JWT tokens designed for browser sessions.

**Recommended approach:** Implement API key authentication alongside (not replacing) existing OAuth/JWT system using a two-hash storage pattern: SHA-256 for fast lookup and Argon2id for secure verification. Keys follow the pattern `och_live_<random>` for easy identification and leak detection. The system integrates with existing authentication middleware via a unified dependency that tries JWT first, then API key, maintaining backward compatibility while enabling new use cases.

**Key risks and mitigation:** The primary risks are timing attacks during validation (mitigated by constant-time comparison), performance degradation from wrong hashing algorithm (mitigated by dual-hash pattern), and rate limit bypasses (mitigated by per-user tracking across all keys). Critical to avoid: using bcrypt/Argon2 alone for every request (200ms+ latency), missing database indexes on lookup columns (35x slowdown), and exposing keys in logs or error messages (immediate compromise). Research shows these are the most common production failures, all preventable through correct Phase 1 design decisions.

## Key Findings

### Recommended Stack

The 2026 stack for API key management has moved away from legacy libraries like passlib (unmaintained since 2020, Python 3.13+ incompatible) toward actively maintained alternatives. The critical insight is that API keys require different hashing than user passwords: passwords need slow hashing (bcrypt/Argon2 at 200-500ms) because authentication is infrequent, but API keys validate on every request and must complete in <50ms.

**Core technologies:**
- **argon2-cffi 25.1.0**: Argon2id hashing for secure verification — PHC winner, 5.6M weekly downloads, Python 3.8-3.14 support
- **secrets (stdlib)**: Cryptographically secure key generation — no dependencies, proven security model
- **hashlib.sha256 (stdlib)**: Fast lookup hash for O(1) database retrieval — enables <5ms first-stage lookup
- **hmac.compare_digest (stdlib)**: Timing-safe comparison — prevents timing attack vulnerabilities (CVE-2026-23996)

**Critical decision:** Use a two-hash pattern. Store both SHA-256 (for fast indexed lookup, ~1-5ms) and Argon2id (for final verification, ~200ms) of the same key. Query by SHA-256 hash first to retrieve the candidate, then verify with Argon2id only if SHA-256 matches. Total validation time: <50ms instead of 200ms+ from Argon2-only approach.

**Existing integration:** The current codebase uses passlib[bcrypt] which should be migrated to argon2-cffi for new API keys while maintaining backward compatibility for existing password hashes. The python-jose[cryptography] JWT library continues to work alongside API keys without modification.

### Expected Features

Research across Stripe, GitHub, OpenAI, and 10+ security best practice guides reveals clear feature tiers for API key management systems.

**Must have (table stakes):**
- Key creation with required name/label — users need to identify which app uses which key
- Show full key once on creation with copy button — industry standard security UX
- Masked display in list (last 4 chars) — never expose full key after creation
- Key revocation with confirmation — essential for security when keys leak
- Hashed storage — SHA-256 for lookup, Argon2id for verification
- Prefixed key format (`och_live_`) — enables leak detection via automated scanning
- Created timestamp — users need to know key age for rotation decisions
- HTTPS-only transmission — already in place via existing security middleware

**Should have (competitive differentiators):**
- Last used timestamp — identifies stale keys for cleanup, enables security auditing
- Optional expiration dates — user flexibility vs. forced rotation (Stripe pattern)
- Per-key rate limiting — isolates abuse to single key, prevents compromised key DoS
- Unlimited keys per user — no artificial limits, user manages complexity
- Dedicated navigation menu — signals developer feature, not buried in settings

**Defer (v2+):**
- Scoped permissions (read-only, write-only) — high complexity, wait for user demand
- IP allowlisting — significant implementation burden, premature optimization
- Key usage analytics dashboard — requires metrics infrastructure not yet built
- Audit logging — important for compliance but not MVP blocker

**Anti-features to avoid:**
- REST API for key management — compromised key can create/revoke others (privilege escalation)
- Retrievable keys after creation — forces reversible storage, major security risk
- Auto-generated names — proliferation of unnamed keys, impossible to identify later
- Mandatory expiration — user friction, breaks automations silently

### Architecture Approach

The architecture extends the existing FastAPI authentication system with a unified dependency pattern that accepts either JWT or API key without requiring endpoint changes. This maintains backward compatibility while enabling new MCP/automation use cases.

**Major components:**

1. **Unified Authentication Dependency** (`auth/dependencies.py`) — FastAPI dependency that tries multiple auth methods in order (JWT Bearer token → Cookie token → X-API-Key header). Returns User object regardless of method used, making authentication transparent to endpoints. Prevents dual-auth confusion by defining clear precedence rules.

2. **ApiKey Model & Service** (`models/api_key.py`, `services/api_key_service.py`) — Encapsulates key lifecycle: generation with `secrets.token_hex(32)`, dual-hash storage (SHA-256 + Argon2id), validation with timing-safe comparison, and revocation. Follows existing codebase patterns (one model per file, service layer for business logic).

3. **API Key CRUD Endpoints** (`api/endpoints/api_keys.py`) — Standard REST operations: POST /api/keys (create), GET /api/keys (list user's keys with masked display), DELETE /api/keys/{id} (revoke), PATCH /api/keys/{id} (update name). Protected by JWT authentication (user must log in to manage keys).

4. **MCP Integration** (`mcp/auth.py`) — Existing `require_user()` function gains API key support transparently by using unified auth dependency. MCP clients send `Authorization: Bearer och_live_xxx` and system validates as API key instead of JWT.

**Data flow insight:** Key creation returns raw key ONCE, storing only hashes. Validation queries by SHA-256 hash (indexed, <5ms), retrieves Argon2id hash, verifies with constant-time comparison, updates last_used_at timestamp. Rate limiting checks occur after successful validation using existing Redis infrastructure (DB 1).

**Critical pattern:** The two-hash storage pattern is non-negotiable for production performance. Research shows bcrypt/Argon2-only validation creates 200-350ms latency, unacceptable for per-request authentication. The SHA-256 first-stage lookup enables <1ms database query, then Argon2id verification only runs on hash match.

### Critical Pitfalls

Research identified 8 major pitfalls from real-world incidents (CVE-2026-23996, vLLM timing attack, GitHub DOGE leak). Top 5 require prevention in Phase 1 design:

1. **Timing Attack Vulnerability** — Using standard string comparison (`==`) instead of constant-time comparison allows attackers to guess keys character-by-character by measuring response time differences. FastAPI's fastapi-api-key library had a CVE for exactly this. **Prevention:** Always use `hmac.compare_digest()` for all key comparisons. Hash incoming keys before comparison (fixed-length hash comparison is inherently safer).

2. **Wrong Hashing Algorithm** — Applying password hashing (bcrypt/Argon2) directly to API keys creates 200-350ms validation times. At scale this causes unacceptable latency and DoS vectors. **Prevention:** Use SHA-256 for fast lookup, Argon2id only for final verification. Security comes from key entropy (256+ bits), not hash slowness.

3. **Missing Database Index** — Full table scans on every API request due to missing index on key_hash column. Documented cases show 35x slowdown (7 seconds → 200ms) from single missing index. **Prevention:** Create composite index on (key_prefix, key_hash_sha256) with partial index on active-only keys. Test with EXPLAIN ANALYZE before deployment.

4. **Key Exposure in Logs** — Full API keys appearing in application logs, error messages, or stored in recoverable form. This is how GitHub DOGE leak exposed government API keys. **Prevention:** Store only prefix + hash (never full key), sanitize Authorization headers in logs, generic error messages ("Invalid API key" not "Key xyz not found").

5. **No Key Prefix** — Opaque random strings without structure make keys impossible to identify in dashboards or during incident response. Users revoke wrong keys. **Prevention:** Use structured format `och_live_<random>` following Stripe/GitHub pattern. Store prefix separately for masked display.

**Additional pitfalls to address in later phases:**
- **Dual auth confusion** (Phase 2): Define explicit precedence (X-API-Key > Bearer JWT > Cookie)
- **Rate limit bypass** (Phase 3): Limit both per-key AND per-user (attacker creates new key per batch)
- **Show-once UX failure** (Phase 4): Require confirmed copy before dismissing key creation modal

## Implications for Roadmap

Based on architecture dependencies and pitfall prevention requirements, suggested phase structure:

### Phase 1: Database Schema & Core Model
**Rationale:** Everything depends on correct schema design. Wrong hashing algorithm, missing indexes, or improper storage patterns require expensive migrations to fix. Must get this right first.

**Delivers:**
- ApiKey SQLAlchemy model with dual-hash fields (key_hash_sha256, key_hash_argon2)
- Database migration with proper indexes: composite on (key_prefix, key_hash_sha256), unique on key_hash_sha256
- User model relationship (user.api_keys)
- Prefix-based key format specification (`och_live_<random>`)

**Addresses features:**
- Hashed storage (table stakes)
- Prefixed key format (table stakes)
- Created timestamp (table stakes)

**Avoids pitfalls:**
- Wrong hashing algorithm (Pitfall 2) — two-hash pattern specified in schema
- Missing database index (Pitfall 3) — indexes created in migration
- No key prefix (Pitfall 5) — format defined in schema

**Research flag:** Standard patterns, skip research-phase. Database schema for API keys is well-documented.

### Phase 2: Validation Service & Auth Integration
**Rationale:** Core business logic must work before exposing CRUD endpoints. Validation is on the critical path for every request, so performance and security are paramount.

**Delivers:**
- ApiKeyService with create_api_key(), validate_api_key(), list_api_keys(), revoke_api_key()
- Constant-time comparison using hmac.compare_digest()
- Unified auth dependency in auth/dependencies.py (JWT → Cookie → API Key precedence)
- MCP auth.py integration using unified dependency

**Addresses features:**
- Key creation with name (table stakes)
- Key validation <50ms (performance requirement)
- Last used timestamp tracking (differentiator)
- Optional expiration checking (differentiator)

**Avoids pitfalls:**
- Timing attack (Pitfall 1) — hmac.compare_digest() in validation
- Dual auth confusion (Pitfall 6) — explicit precedence rules
- Key exposure in logs (Pitfall 4) — log sanitization in validation

**Uses stack:**
- argon2-cffi for secure verification hash
- secrets for random token generation
- hashlib.sha256 for fast lookup hash

**Research flag:** Standard patterns, skip research-phase. FastAPI authentication patterns are well-established.

### Phase 3: CRUD API Endpoints
**Rationale:** Depends on working validation service and auth. Enables UI development. Rate limiting logic belongs here because it's enforced at endpoint level.

**Delivers:**
- POST /api/keys (create) — returns raw key once, stores only hashes
- GET /api/keys (list) — returns masked keys with metadata
- DELETE /api/keys/{id} (revoke) — soft delete via is_active flag
- PATCH /api/keys/{id} (update name)
- Per-key rate limiting using existing Redis infrastructure
- Per-user key count limits (max 10 active keys)

**Addresses features:**
- Key revocation (table stakes)
- Unlimited keys per user (differentiator) — enforced at reasonable limit
- Per-key rate limiting (differentiator)

**Avoids pitfalls:**
- Rate limit bypass (Pitfall 7) — per-user tracking across all keys

**Implements architecture:**
- API Key CRUD Endpoints component
- Integration with existing Redis rate limiting (DB 1)

**Research flag:** Standard patterns, skip research-phase. CRUD endpoints follow existing codebase patterns.

### Phase 4: Frontend UI
**Rationale:** Depends on working backend API. UX is critical for key management — show-once flow must prevent accidental key loss.

**Delivers:**
- API Keys settings page (app/settings/api-keys/page.tsx)
- Create key modal with confirmation flow (require copy before dismiss)
- Key list view with masked display (och_live_****1234)
- Revocation confirmation dialog
- "Last used" and expiration display

**Addresses features:**
- Show full key once with copy button (table stakes)
- Masked display in list (table stakes)
- Key revocation with confirmation (table stakes)
- Dedicated navigation menu (differentiator)

**Avoids pitfalls:**
- Show-once UX failure (Pitfall 8) — confirmed copy flow
- No key naming (UX pitfall) — required name field
- Revocation without confirmation (UX pitfall) — confirmation dialog

**Implements architecture:**
- Frontend Key Management component

**Research flag:** Standard patterns, skip research-phase. Settings UI follows existing patterns in codebase.

### Phase Ordering Rationale

**Why Phase 1 first:**
- Schema mistakes require expensive migrations (wrong hash algorithm documented as MEDIUM recovery cost)
- Missing indexes cause 35x slowdown, caught early prevent production issues
- Prefix format cannot be retrofitted to existing keys (MEDIUM recovery cost)

**Why Phase 2 before Phase 3:**
- CRUD endpoints depend on working validation service
- Timing attack vulnerability must be prevented in core validation, not patched later (LOW recovery cost but critical security)
- Unified auth dependency enables MCP integration without waiting for full CRUD UI

**Why Phase 4 last:**
- Frontend can be developed independently once API stable
- Show-once UX testing requires working backend
- Iterating on UX doesn't block backend functionality

**Dependency chain:**
Schema → Service → API → UI (strictly sequential, no parallelization)

### Research Flags

**Phases with standard patterns (skip research-phase during planning):**
- **Phase 1:** Database schema for API keys is well-documented across Stripe, GitHub, OpenAI patterns
- **Phase 2:** FastAPI authentication dependencies follow existing codebase patterns
- **Phase 3:** CRUD endpoints match existing endpoint patterns (rootly, integrations)
- **Phase 4:** Settings UI follows existing patterns (integration management)

**No phases require deeper research** — all patterns are proven and documented. The high confidence in Stack, Features, Architecture, and Pitfalls research means roadmap planning can proceed directly to requirements definition.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Verified against PyPI (argon2-cffi 25.1.0, June 2025), official docs, FastAPI reference. Migration path from passlib documented. |
| Features | HIGH | Synthesized from 4 major competitors (Stripe, GitHub, OpenAI, Datadog) and 10+ security guides. Clear consensus on table stakes vs. differentiators. |
| Architecture | HIGH | Extends existing On-Call Health patterns (auth/dependencies.py, models/, services/). Unified auth dependency proven in production codebases. |
| Pitfalls | HIGH | Based on real CVEs (CVE-2026-23996), production incidents (vLLM timing attack, GitHub DOGE leak), and documented recovery costs. |

**Overall confidence:** HIGH

All four research streams converged on consistent recommendations:
- Stack research identified the two-hash pattern as industry standard
- Features research confirmed last_used tracking as competitive differentiator
- Architecture research specified unified auth dependency for existing system integration
- Pitfalls research validated timing attack as #1 risk requiring constant-time comparison

No contradictions between research streams. Recommendations are internally consistent.

### Gaps to Address

**Minor gaps (manageable during implementation):**

1. **Rate limiting granularity** — Research shows per-key and per-user limits needed, but exact thresholds (5/minute per key? 50/minute per user?) should be tuned during Phase 3 load testing. Start conservative, monitor, adjust.

2. **Key format specifics** — Prefix `och_live_` confirmed, but environment separation (test vs. production) may need refinement based on deployment architecture. Current codebase has single environment, so `och_live_` sufficient for v1.

3. **Audit logging scope** — Pitfalls research flags audit logging as important but defers to v2+. During Phase 2-3 implementation, decide: log all validations (high volume) or only CRUD operations (lower volume)? Start with CRUD-only, add validation logging if compliance requires.

**No blocking gaps** — all critical decisions resolved by research. These are tuning parameters, not architectural unknowns.

## Sources

### Primary (HIGH confidence)
- [argon2-cffi PyPI](https://pypi.org/project/argon2-cffi/) — Version 25.1.0 verified, Python compatibility
- [argon2-cffi Documentation](https://argon2-cffi.readthedocs.io/) — Implementation patterns
- [FastAPI Security Reference](https://fastapi.tiangolo.com/reference/security/) — APIKeyHeader official docs
- [Python secrets module](https://docs.python.org/3/library/secrets.html) — Stdlib reference
- [PostgreSQL Hash Indexes](https://www.postgresql.org/docs/current/hash-index.html) — Performance characteristics

### Secondary (MEDIUM confidence)
- [Stripe API Keys](https://docs.stripe.com/keys) — Key format patterns
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens) — Prefix standards
- [OpenAI API Authentication](https://platform.openai.com/docs/api-reference/authentication) — Best practices
- [Google Cloud API Keys Best Practices](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices) — Security guidelines
- [How prefix.dev Implemented API Keys](https://prefix.dev/blog/how_we_implented_api_keys) — Real-world implementation

### Security Advisories
- [CVE-2026-23996](https://dev.to/cverports/cve-2026-23996-the-tell-tale-delay-timing-side-channels-in-fastapi-api-key-5e5m) — Timing attack in fastapi-api-key
- [vLLM GHSA-wr9h-g72x-mwhm](https://github.com/vllm-project/vllm/security/advisories/GHSA-wr9h-g72x-mwhm) — API key timing vulnerability
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) — Hashing guidelines

---
*Research completed: 2026-01-30*
*Ready for roadmap: yes*
