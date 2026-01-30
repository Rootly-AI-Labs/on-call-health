# Requirements: API Key Management

**Project:** API Key Management for On-Call Health
**Generated:** 2026-01-30
**Status:** Active

## Functional Requirements

### Key Lifecycle Management

**REQ-F-001: API Key Creation**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements
System shall allow authenticated users to create new API keys with a required name field.
- Name field is required (cannot be empty)
- Name must be unique per user
- User can create unlimited keys
- Success returns full key value (shown once only)

**REQ-F-002: Prefixed Key Format**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Table Stakes
System shall generate API keys with prefix format `och_live_<random>`.
- Prefix: `och_live_`
- Random portion: 32 characters (190 bits entropy)
- Use cryptographically secure random generation (`secrets.token_hex()`)
- Format enables log scanning and leak detection

**REQ-F-003: Show Full Key Once**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Table Stakes, FEATURES.md - Security
System shall display the full API key value only once during creation.
- Full key shown immediately after creation
- Copy-to-clipboard button provided
- Clear warning: "This is the only time you'll see this key"
- Key never retrievable after creation modal closes

**REQ-F-004: Copy-to-Clipboard**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Table Stakes
System shall provide one-click copy functionality for newly created keys.
- Single click copies full key to clipboard
- Visual feedback: "Copied!" confirmation
- Prevent manual copy errors

**REQ-F-005: Key Revocation**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - Table Stakes
System shall allow users to revoke API keys without affecting web session.
- Revocation is immediate
- Confirmation dialog required before revocation
- Dialog shows key name for verification
- Revoked keys cannot authenticate
- Revocation does not affect user's JWT session

**REQ-F-006: Revocation Confirmation Dialog**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Table Stakes
System shall require explicit confirmation before revoking a key.
- Title: "Revoke API Key?"
- Body: Display key name and warning about breaking applications
- Actions: "Cancel" (secondary), "Revoke" (danger/red)
- Prevent accidental deletion

**REQ-F-007: Optional Expiration Date**
**Priority:** P1 (High)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - MVP v1
System shall support optional expiration dates for API keys.
- User can choose: Never, 30 days, 90 days, 1 year, Custom
- Default: Never (no expiration)
- Expired keys automatically rejected during validation
- No email notifications (out of scope for v1)

**REQ-F-008: Unlimited Keys Per User**
**Priority:** P1 (High)
**Source:** PROJECT.md - Key Decisions, FEATURES.md - MVP v1
System shall not impose artificial limits on number of keys per user.
- No maximum key count enforced
- User manages their own key complexity
- Performance considerations handled via indexing

### Key Display and Metadata

**REQ-F-009: Key List View**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Table Stakes
System shall display a list of all API keys for the authenticated user.
- Table format with columns: Name, Key, Created, Last Used, Expires, Actions
- Sortable by creation date (most recent first)
- Masked key display (see REQ-F-010)
- Empty state: "No API keys yet. Create your first key to get started."

**REQ-F-010: Masked Key Display**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - Table Stakes
System shall display only the last 4 characters of API keys after creation.
- Format: `och_live_****1234`
- Full key never displayed after creation modal closes
- Security requirement: prevent shoulder surfing

**REQ-F-011: Created Timestamp**
**Priority:** P1 (High)
**Source:** FEATURES.md - Table Stakes
System shall record and display when each key was created.
- Stored as UTC timestamp in database
- Displayed in user's local timezone
- Format: "Jan 30, 2026" or relative time "2 hours ago"

**REQ-F-012: Last Used Timestamp**
**Priority:** P1 (High)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - MVP v1
System shall track and display when each key was last used.
- Updated on each successful authentication
- Displayed as: "Never used", "2 hours ago", or absolute date
- Helps identify stale keys for cleanup
- Update must not add >10ms latency to auth flow

### Authentication and Security

**REQ-F-013: Hashed Storage**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - Table Stakes
System shall hash API keys before storage using secure algorithm.
- Dual-hash pattern: SHA-256 for fast lookup + Argon2id for verification
- SHA-256 indexed for <50ms lookups
- Argon2id provides cryptographic security
- Plaintext key never stored in database
- Hash computed immediately on creation

**REQ-F-014: Dual Authentication Support**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements, ARCHITECTURE.md
System shall support both JWT tokens and API keys for authentication.
- Unified authentication dependency
- Precedence order: JWT header → Cookie → API Key header
- MCP server accepts both auth methods during migration
- No breaking changes to existing JWT authentication
- Authorization header format: `Bearer <token_or_key>`

**REQ-F-015: Per-Key Rate Limiting**
**Priority:** P1 (High)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - MVP v1
System shall apply rate limits per API key, separate from user rate limit.
- Each key has independent rate limit counter
- Default: 100 requests/minute per key
- Prevents single compromised key from exhausting user's quota
- Redis-backed rate limit tracking
- HTTP 429 response when limit exceeded

**REQ-F-016: HTTPS Transmission Only**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Table Stakes
System shall ensure API keys are never transmitted over unencrypted connections.
- Enforce HTTPS in production
- Security middleware already in place
- Reject HTTP requests with API keys

**REQ-F-017: Full Access Scope Only (v1)**
**Priority:** P1 (High)
**Source:** PROJECT.md - Active Requirements, Key Decisions
System shall support only "full_access" scope in v1.
- All v1 keys have full API access
- Scope field present in database for v2 extensibility
- Granular scopes (read-only, write-only) deferred to v2
- Simplifies v1 implementation

### User Interface

**REQ-F-018: Dedicated API Keys Navigation**
**Priority:** P1 (High)
**Source:** PROJECT.md - Active Requirements, Key Decisions
System shall provide dedicated "API Keys" navigation menu item.
- Top-level menu item in user dropdown
- Not buried in Account Settings
- Signals developer feature
- Direct route: `/dashboard/api-keys`

**REQ-F-019: Key Creation UI**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements
System shall provide UI for creating new API keys.
- Modal dialog triggered by "Create API Key" button
- Name field (required, placeholder: "Claude Desktop")
- Expiration dropdown (Never, 30 days, 90 days, 1 year, Custom)
- Submit button: "Create Key"
- Success modal shows full key with copy button and warning

**REQ-F-020: Key List UI**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements, FEATURES.md - UX Patterns
System shall display key list in table format with all metadata.
- Columns: Name, Key (masked), Created, Last Used, Expires, Actions
- "Revoke" button per key
- Empty state message
- Responsive design for mobile

**REQ-F-021: Key Revocation UI**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Active Requirements
System shall provide UI for revoking keys with confirmation.
- "Revoke" button in Actions column
- Confirmation modal (see REQ-F-006)
- List refreshes after successful revocation
- Success toast notification

## Non-Functional Requirements

### Performance

**REQ-NF-001: Fast Key Validation**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Constraints, ARCHITECTURE.md
System shall validate API keys in under 50ms (p95).
- SHA-256 hash lookup indexed in database
- No additional latency to API requests
- Acceptable: ~1 minute cache propagation delay for revocation

**REQ-NF-002: Database Indexing**
**Priority:** P0 (Critical)
**Source:** PITFALLS.md
System shall create indexes on key lookup fields.
- Index on `key_hash` (SHA-256) for fast lookups
- Index on `user_id` for key list queries
- Index on `last_used_at` for activity tracking
- Prevents 35x performance degradation

**REQ-NF-003: Async Last Used Update**
**Priority:** P1 (High)
**Source:** FEATURES.md - Dependencies
System shall update `last_used_at` asynchronously to avoid blocking auth flow.
- Fire-and-forget update after successful auth
- Does not block request processing
- Eventual consistency acceptable

### Security

**REQ-NF-004: Timing-Safe Comparison**
**Priority:** P0 (Critical)
**Source:** PITFALLS.md, STACK.md
System shall use constant-time comparison for key validation.
- Use `hmac.compare_digest()` for hash comparison
- Prevents timing attack vulnerabilities (CVE-2026-23996)
- Critical for security

**REQ-NF-005: Cryptographically Secure Random**
**Priority:** P0 (Critical)
**Source:** STACK.md
System shall generate keys using cryptographically secure random number generator.
- Use Python `secrets.token_hex(32)` (not `random` module)
- Provides 190 bits of entropy
- Prevents predictable key generation

**REQ-NF-006: No Plaintext Storage**
**Priority:** P0 (Critical)
**Source:** FEATURES.md - Anti-Features
System shall never store API keys in plaintext or reversible encryption.
- Hash-only storage (dual-hash pattern)
- No decryption capability
- Regeneration required if key lost

### Compatibility

**REQ-NF-007: Backward Compatibility with JWT**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Constraints, ARCHITECTURE.md
System shall maintain full compatibility with existing JWT authentication.
- No breaking changes to JWT flow
- Both auth methods work simultaneously
- Existing users unaffected
- MCP clients can gradually migrate

**REQ-NF-008: Existing Stack Compatibility**
**Priority:** P0 (Critical)
**Source:** PROJECT.md - Constraints
System shall integrate with existing FastAPI + SQLAlchemy + PostgreSQL stack.
- No new database engines
- Use existing Redis instance
- Follow existing authentication patterns
- SQLAlchemy ORM models

### Observability

**REQ-NF-009: Structured Logging**
**Priority:** P1 (High)
**Source:** ARCHITECTURE.md - Cross-Cutting Concerns
System shall log key lifecycle events with structured context.
- Key creation: user_id, key_id, expiration
- Key revocation: user_id, key_id, revoked_by
- Failed auth: key_id (masked), reason
- Use existing UserContextFilter for consistency

**REQ-NF-010: Error Messages**
**Priority:** P1 (High)
**Source:** ARCHITECTURE.md - Error Handling
System shall provide clear, actionable error messages for auth failures.
- "Invalid API key" - generic message (don't reveal if key exists)
- "API key has expired" - includes expiration date
- "API key revoked" - suggests creating new key
- "Rate limit exceeded" - includes retry-after timestamp

## Out of Scope (Explicitly Deferred)

**OOS-001: REST API for Key Management**
**Reason:** Security - prevents compromised key from creating/revoking other keys
**Source:** PROJECT.md - Out of Scope, FEATURES.md - Anti-Features
**Future:** Only if strong use case emerges

**OOS-002: IP Address Restrictions**
**Reason:** High complexity, wait for user demand
**Source:** PROJECT.md - Out of Scope
**Future:** v2+ if needed

**OOS-003: Audit Logging**
**Reason:** Can add later if compliance requirements emerge
**Source:** PROJECT.md - Out of Scope
**Future:** v1.x when needed

**OOS-004: Request Count Tracking**
**Reason:** Can add later when users request usage insights
**Source:** PROJECT.md - Out of Scope
**Future:** v1.x

**OOS-005: Granular Permission Scopes**
**Reason:** Ship v1 faster, add read-only/write-only scopes in v2
**Source:** PROJECT.md - Key Decisions
**Future:** v2 when users request granularity

**OOS-006: Test Button in UI**
**Reason:** Creates edge cases with rate limits, documentation examples sufficient
**Source:** FEATURES.md - Anti-Features
**Future:** Not planned

**OOS-007: Email Notifications for Expiry**
**Reason:** Infrastructure complexity, spam concerns
**Source:** FEATURES.md - Anti-Features
**Future:** Dashboard warnings instead (v1.x)

**OOS-008: Automatic Key Rotation**
**Reason:** Breaks integrations silently, manual rotation safer
**Source:** FEATURES.md - Anti-Features
**Future:** Not planned

**OOS-009: Retrievable Keys**
**Reason:** Security - forces plaintext storage, major vulnerability
**Source:** FEATURES.md - Anti-Features
**Future:** Never (security principle)

## Requirements Traceability

### PROJECT.md → Requirements Mapping

| PROJECT.md Requirement | REQ-ID | Status |
|------------------------|--------|--------|
| API key model | REQ-F-001, REQ-F-011, REQ-F-012 | Defined |
| Generate with prefix | REQ-F-002 | Defined |
| Hash before storage | REQ-F-013 | Defined |
| Revoke without affecting session | REQ-F-005 | Defined |
| Display last 4 chars only | REQ-F-010 | Defined |
| Show full key once | REQ-F-003 | Defined |
| Track last used | REQ-F-012 | Defined |
| Optional expiration | REQ-F-007 | Defined |
| Unlimited keys | REQ-F-008 | Defined |
| Per-key rate limiting | REQ-F-015 | Defined |
| Full access scope only | REQ-F-017 | Defined |
| Dedicated navigation | REQ-F-018 | Defined |
| Creation UI | REQ-F-019 | Defined |
| List UI | REQ-F-020 | Defined |
| Revocation UI | REQ-F-021 | Defined |
| Dual auth support | REQ-F-014 | Defined |

### FEATURES.md → Requirements Mapping

| Feature Category | REQ-IDs | Status |
|------------------|---------|--------|
| Table Stakes (10 features) | REQ-F-001 to REQ-F-011, REQ-F-016 | Defined |
| Differentiators (v1 subset) | REQ-F-012, REQ-F-015, REQ-F-017, REQ-F-018 | Defined |
| Anti-Features (avoided) | OOS-001 to OOS-009 | Explicitly deferred |

## Requirements Summary

**Total Requirements:** 31
- Functional: 21 (REQ-F-001 to REQ-F-021)
- Non-Functional: 10 (REQ-NF-001 to REQ-NF-010)
- Out of Scope: 9 (OOS-001 to OOS-009)

**Priority Breakdown:**
- P0 (Critical): 15 requirements
- P1 (High): 6 requirements

**Coverage:**
- All PROJECT.md active requirements mapped ✓
- All FEATURES.md v1 MVP features mapped ✓
- All ARCHITECTURE.md constraints captured ✓
- All PITFALLS.md concerns addressed ✓

---

*Generated: 2026-01-30*
*Next: Create roadmap with phase breakdown*
