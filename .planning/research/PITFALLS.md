# Pitfalls Research

**Domain:** API Key Management for Existing Authentication System
**Researched:** 2026-01-30
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Timing Attack Vulnerability in Key Validation

**What goes wrong:**
Using standard string comparison (`==` or `===`) to validate API keys allows attackers to guess keys character-by-character by measuring response time differences. A real vulnerability (CVE-2026-23996) was discovered in fastapi-api-key for exactly this issue. The vLLM project also disclosed a similar timing attack vulnerability in their API key validation.

**Why it happens:**
Standard string comparison exits early on first mismatch. More matching characters = longer comparison time. Attackers can statistically determine correct characters by measuring microsecond differences across many requests.

**How to avoid:**
- Use constant-time comparison functions: `hmac.compare_digest()` in Python or `crypto.timingSafeEqual()` in Node.js
- Hash the incoming key before comparison (comparing hashes is safer since they're fixed length)
- Implement aggressive rate limiting to disrupt statistical timing analysis (already have 5/minute for admin_api_key)

**Warning signs:**
- Using `==` or `if key == stored_key` anywhere in validation code
- API key validation endpoint response times vary with input
- Security scanners flagging timing vulnerabilities

**Phase to address:**
Phase 1 (Database Schema & Core Model) - Build constant-time comparison into the validation function from day one.

---

### Pitfall 2: Using Password Hashing (bcrypt/Argon2) for API Key Storage

**What goes wrong:**
Developers apply password hashing best practices (bcrypt, Argon2id) to API keys, resulting in 200-350ms validation times instead of the required <50ms. At scale, this creates unacceptable latency and potential DoS vectors.

**Why it happens:**
Password hashing algorithms are intentionally slow (work factor 12+ for bcrypt = 250ms+). Developers correctly learn "always hash credentials" but don't distinguish between user-facing password authentication (infrequent, one-off) and API key validation (every single request).

**How to avoid:**
- Use fast cryptographic hashes with HMAC: `HMAC-SHA256(key, server_secret)` or plain `SHA-256` of the full key
- The security comes from key entropy (256+ bits), not hash slowness
- Reserve bcrypt/Argon2 for user passwords only
- Store: `sha256(prefix + long_token)` - lookup by prefix, compare hash

**Warning signs:**
- API key validation exceeding 50ms in load tests
- Database CPU spiking on authentication checks
- Validation time scales with bcrypt work factor adjustments

**Phase to address:**
Phase 1 (Database Schema) - Select SHA-256 or HMAC-SHA256 for key hashing, not bcrypt.

---

### Pitfall 3: Missing or Incorrect Database Index on Key Lookup Column

**What goes wrong:**
Full table scans on every API request because the hashed key column lacks a proper index. Query times of 200ms+ instead of <1ms. A single missing index has been documented to cause 35x slowdown (7 seconds to 200ms in production cases).

**Why it happens:**
Developers create the `api_keys` table but forget to index the lookup column. Or they index the full hash but query by prefix. Or they create a regular index instead of a unique index, missing integrity enforcement.

**How to avoid:**
- Use composite primary key: `(prefix, key_hash)` - prefix for lookup, hash for verification
- Add unique constraint on key_hash to prevent accidental duplicates
- Create covering index that includes commonly-needed fields (user_id, expires_at, is_active)
- Test with EXPLAIN ANALYZE before deployment

**Warning signs:**
- Slow query logs showing seq scans on api_keys table
- p99 latency spikes on authenticated endpoints
- Database load increases linearly with key count

**Phase to address:**
Phase 1 (Database Schema) - Define indexes in migration, verify with EXPLAIN ANALYZE.

---

### Pitfall 4: Exposing Full API Key in Logs, Error Messages, or Database

**What goes wrong:**
Full API keys appear in application logs, error responses, or stored in recoverable form. Attackers with log access gain immediate API access. This is how the DOGE employee leak exposed government API keys via GitHub.

**Why it happens:**
- Logging request headers without filtering sensitive values
- Returning helpful error messages like "Invalid key: sk_live_abc123..."
- Storing keys encrypted (recoverable) instead of hashed (one-way)
- Debug mode accidentally enabled in production

**How to avoid:**
- Store only: `prefix` (for identification) + `hash(full_key)` (for verification)
- Never store the full key - show it exactly once at creation time
- Sanitize all logs: mask Authorization headers
- Generic error messages: "Invalid API key" not "Key xyz not found"
- Add prefix to keys (e.g., `och_live_`, `och_test_`) to identify leaked keys via automated scanning

**Warning signs:**
- Grep for API key patterns in log files
- Error responses contain partial key information
- Database has a decryptable `key` column instead of `key_hash`

**Phase to address:**
Phase 1 (Core Model) - Design schema with hash-only storage; Phase 2 (CRUD API) - Implement log sanitization.

---

### Pitfall 5: No Key Prefix for Identification and Revocation

**What goes wrong:**
Users have multiple keys but cannot identify which key is which in their dashboard. When a key is compromised, they revoke the wrong one. Operations cannot quickly identify which service a leaked key belongs to.

**Why it happens:**
Developers generate opaque random strings without structure. Works fine with one key, becomes unusable with multiple keys or in incident response.

**How to avoid:**
- Use structured format: `{service_prefix}_{environment}_{short_token}_{long_token}`
- Example: `och_live_abc123_[64-char-secret]`
- Store and display short_token for identification (safe to show)
- Only hash/verify long_token (never displayable after creation)
- Stripe pattern: `sk_live_`, `sk_test_`, `pk_live_`, `pk_test_`

**Warning signs:**
- User support tickets about "which key is which"
- Incident response delayed by key identification
- Users regenerating all keys instead of revoking one

**Phase to address:**
Phase 1 (Core Model) - Design key format with prefix structure.

---

### Pitfall 6: Dual Authentication Mode Without Clear Precedence Rules

**What goes wrong:**
During migration, both JWT and API keys are accepted. Conflicting authentication methods on same request cause unpredictable behavior. Middleware processes JWT first, then API key, resulting in wrong user context or authorization failures.

**Why it happens:**
Adding API key auth to existing JWT system without defining precedence. The current `get_current_user()` function in `dependencies.py` checks Authorization header then cookies - adding API keys requires a third path with clear priority.

**How to avoid:**
- Define explicit precedence: API Key header > Bearer JWT > Cookie
- Document which auth method was used in request context for logging/debugging
- Reject requests with multiple auth methods (or pick one consistently)
- Use different headers: `X-API-Key` vs `Authorization: Bearer`

**Warning signs:**
- Tests pass individually but fail when auth methods combined
- Logs show user A's request authorized as user B
- "Works sometimes" authentication bugs

**Phase to address:**
Phase 2 (Validation Service) - Implement unified auth dispatcher with clear precedence.

---

### Pitfall 7: Rate Limiting Bypassed by Generating New Keys

**What goes wrong:**
Rate limits are per-key, but users can generate unlimited keys. Attacker creates new key for each batch of requests, effectively bypassing all rate limits.

**Why it happens:**
Rate limiting implemented per-key without considering key creation as an attack vector. Current system has `admin_api_key: 5/minute` but this only limits key validation, not key creation.

**How to avoid:**
- Rate limit key creation: max 10 keys per user, 3 new keys per hour
- Rate limit at user level, not just key level
- Track request volume across all user's keys
- Implement organization-level quotas

**Warning signs:**
- Users with dozens of active keys
- Burst traffic from many keys belonging to same user
- Key creation spikes before abuse incidents

**Phase to address:**
Phase 2 (CRUD API) - Enforce key count limits; Phase 3 (Rate Limiting) - Implement per-user rate tracking.

---

### Pitfall 8: Show-Once Key Revealed Before User Confirms Copy

**What goes wrong:**
Key displayed immediately on creation. User navigates away accidentally. Key is lost forever. Support tickets flood in for "lost key" recovery (which is impossible by design).

**Why it happens:**
Standard form flow: submit -> success message with key. No user confirmation that they've saved it.

**How to avoid:**
- Two-step reveal: Create key -> Show "key created" with masked preview -> User clicks "Reveal key" -> Copy button -> "I've saved this key" confirmation
- Require clipboard copy or download before dismissing
- Send one-time-viewable key via secure channel as backup option
- Clear UX warning: "This key will only be shown once. Store it securely."

**Warning signs:**
- Support tickets asking to recover lost keys
- Users immediately regenerating keys after creation
- Low key usage rate (users create but never use)

**Phase to address:**
Phase 4 (Frontend UI) - Implement confirmed reveal flow.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Store encrypted keys (not hashed) | Keys recoverable for support | Database breach = all keys compromised | Never for production API keys |
| Skip key expiration | Simpler implementation | Stale keys accumulate, never rotated | Never - at minimum support optional expiration |
| Single global rate limit | Quick to implement | No per-key/per-user granularity | MVP only, with plan to enhance |
| No key prefix format | Faster generation | Cannot identify keys in logs/incidents | Never - always use prefixes |
| In-memory rate limiting | No Redis dependency | Distributed bypass, state loss on restart | Development only (already handled in codebase) |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| MCP Authentication | Passing JWT where API key expected | MCP should accept API keys exclusively; separate from web auth |
| Existing JWT system | Modifying `get_current_user()` directly | Create `get_current_user_or_api_key()` wrapper, keep JWT logic intact |
| Redis rate limiting | Using same database as app | Already correct - using DB 1 for rate limiting. Continue this pattern for API key rate tracking |
| Frontend token storage | Treating API keys like JWTs | API keys should never touch frontend; backend-to-backend only |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| bcrypt for key validation | 200-300ms per request | Use SHA-256/HMAC, target <5ms | Any production load |
| Missing index on key_hash | p99 > 100ms, linear scaling | Composite index on (prefix, key_hash) | >1000 keys |
| N+1 queries for key metadata | Load user/org on every request | Eager load in single query or cache | >100 requests/second |
| Hash computation in Python | CPU bottleneck | Use hashlib (C bindings) not pure Python | >500 validations/second |
| Logging every validation | Log volume explosion | Sample logging, metrics instead | >1000 requests/minute |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Timing attack in comparison | Key can be guessed character-by-character | `hmac.compare_digest()` always |
| Key in URL parameters | Logged in server/proxy access logs | Header only (`X-API-Key` or `Authorization`) |
| Weak key entropy | Brute force possible | 256-bit minimum (32 bytes = 43 base64 chars) |
| No key scope/permissions | All-or-nothing access | Plan for scoped keys even if v1 is full-access |
| Accepting expired keys | Revocation doesn't work | Check expiration on every validation |
| Missing audit log | Cannot investigate breaches | Log: key_id (not key), timestamp, endpoint, IP |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Key shown then immediately hidden | User didn't copy in time, lost forever | Reveal flow with confirmation, copy button |
| No key naming/description | "Which key is for which service?" | Required name field, optional description |
| Immediate key creation | Accidental key proliferation | Confirmation modal with security reminder |
| No last-used timestamp | Cannot identify stale keys for cleanup | Track and display last successful authentication |
| Revocation without confirmation | Accidental production outage | "Type key name to confirm" for active keys |
| No partial key display | Cannot identify keys in dashboard | Show prefix + last 4 chars: `och_live_...x7Kp` |

## "Looks Done But Isn't" Checklist

- [ ] **Key validation:** Constant-time comparison implemented - verify with timing analysis
- [ ] **Key storage:** Only hash stored, never recoverable - check database schema directly
- [ ] **Rate limiting:** Per-user limits, not just per-key - test with multiple keys
- [ ] **Logging:** Keys never appear in logs - grep production logs for key patterns
- [ ] **Error messages:** Generic "Invalid key" only - test invalid key error response
- [ ] **Key expiration:** Optional expiry actually enforced - test with expired key
- [ ] **Audit trail:** All authentications logged with key_id - verify audit table populated
- [ ] **Index performance:** EXPLAIN ANALYZE shows index scan - test with 10k+ keys
- [ ] **Dual auth:** JWT and API key precedence tested - send request with both

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Timing attack vulnerability | LOW | Add `hmac.compare_digest()`, deploy immediately |
| Wrong hashing algorithm (bcrypt) | MEDIUM | Migration: add sha256 column, backfill, switch validation, drop bcrypt column |
| Missing index | LOW | Add index (online in Postgres), immediate improvement |
| Keys in logs | HIGH | Rotate all potentially-exposed keys, audit log access, implement log sanitization |
| No key prefix | MEDIUM | Cannot retrofit existing keys - deprecate and require new keys with prefix |
| Rate limit bypass | MEDIUM | Add per-user tracking, may require key regeneration for quota assignment |
| Lost key (show-once failure) | LOW per incident | User regenerates key - but high support volume if UX poor |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Timing attack | Phase 1: Core Model | Code review for `hmac.compare_digest()` |
| Wrong hash algorithm | Phase 1: Schema Design | Verify SHA-256/HMAC, not bcrypt |
| Missing index | Phase 1: Migration | EXPLAIN ANALYZE on validation query |
| Key exposure in logs | Phase 2: CRUD API | Grep logs for key patterns after test run |
| No key prefix | Phase 1: Core Model | Key format regex validation |
| Dual auth confusion | Phase 2: Validation | Integration tests with both auth methods |
| Rate limit bypass | Phase 3: Rate Limiting | Load test with multiple keys per user |
| Show-once UX | Phase 4: Frontend | User testing of key creation flow |
| No audit trail | Phase 2: CRUD API | Verify audit entries after each operation |

## Sources

- [CVE-2026-23996: Timing Side-Channels in fastapi-api-key](https://dev.to/cverports/cve-2026-23996-the-tell-tale-delay-timing-side-channels-in-fastapi-api-key-5e5m)
- [vLLM API Key Timing Attack Advisory](https://github.com/vllm-project/vllm/security/advisories/GHSA-wr9h-g72x-mwhm)
- [OWASP Password Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
- [Password Hashing Guide 2025: Argon2 vs Bcrypt vs Scrypt vs PBKDF2](https://guptadeepak.com/the-complete-guide-to-password-hashing-argon2-vs-bcrypt-vs-scrypt-vs-pbkdf2-2026/)
- [How prefix.dev Implemented API Keys](https://prefix.dev/blog/how_we_implented_api_keys)
- [Hashing API Keys To Improve Security - Octopus Deploy](https://octopus.com/blog/hashing-api-keys)
- [API Key Authentication Best Practices - Zuplo](https://zuplo.com/blog/2022/12/01/api-key-authentication)
- [FreeCodeCamp: Best Practices for Building Secure API Keys](https://www.freecodecamp.org/news/best-practices-for-building-api-keys-97c26eabfea9/)
- [Stripe API Keys Documentation](https://docs.stripe.com/keys)
- [API Rate Limiting 2026 - Levo.ai](https://www.levo.ai/resources/blogs/api-rate-limiting-guide-2026)
- [Migrating from API Keys to OAuth 2.1 - Scalekit](https://www.scalekit.com/blog/migrating-from-api-keys-to-oauth-mcp-servers)

---
*Pitfalls research for: API Key Management*
*Researched: 2026-01-30*
