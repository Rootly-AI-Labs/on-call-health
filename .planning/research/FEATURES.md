# Feature Research: API Key Management

**Domain:** API key management for SaaS/developer tools
**Researched:** 2026-01-30
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Key creation with name/label** | Users need to identify which app uses which key | LOW | Standard text input, required field |
| **Show full key once on creation** | Industry standard (GitHub, Stripe, OpenAI) - security requirement | LOW | Modal with copy button, clear warning |
| **Copy-to-clipboard button** | Manual copying is error-prone, expected UX | LOW | Single click, visual feedback |
| **Key list view** | Users need to see and manage existing keys | LOW | Table with name, masked key, dates |
| **Masked display (last 4 chars)** | Security: never show full key after creation | LOW | Display as `och_live_****1234` |
| **Key revocation** | Essential for security when keys leak or apps decommissioned | LOW | Button with confirmation dialog |
| **Confirmation dialog for revocation** | Prevent accidental deletion, revocation is irreversible | LOW | "Are you sure?" with key name shown |
| **Created timestamp** | Users need to know key age for rotation | LOW | Part of key metadata |
| **Hashed storage** | Security: plaintext storage is unacceptable | MEDIUM | SHA-256 recommended for API keys |
| **Prefixed key format** | Industry standard: `sk_`, `pk_`, `och_live_` - helps identify leaked keys in logs | LOW | Generate with prefix during creation |
| **HTTPS transmission only** | Keys must never traverse unencrypted connections | LOW | Already in place via existing security middleware |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Last used timestamp** | Identify stale keys for cleanup, security auditing | MEDIUM | Update on each authenticated request - requires fast lookup |
| **Optional expiration dates** | User flexibility vs forced rotation | LOW | Nullable date field, check on validation |
| **Per-key rate limiting** | Isolate abuse to single key, prevent compromised key DoS | MEDIUM | Requires Redis key structure per API key |
| **Unlimited keys per user** | No artificial limits, user manages their complexity | LOW | No enforcement needed |
| **Dedicated navigation menu** | Signals developer feature, not buried in settings | LOW | Frontend routing addition |
| **Scoped permissions (v2)** | Least privilege principle, limit blast radius | HIGH | Requires permission model, UI for scope selection |
| **IP allowlisting (v2)** | Additional security layer for sensitive integrations | HIGH | Per-key IP list, validation on each request |
| **Key usage analytics** | Show request counts, success/error rates per key | HIGH | Requires metrics collection, dashboard |
| **Audit logging** | Track key creation, revocation, usage for compliance | MEDIUM | Event logging infrastructure |
| **Request count tracking** | Show total API calls per key | MEDIUM | Counter per key in Redis |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **REST API for key management** | "API-first" philosophy, automation | Compromised key can create/revoke other keys, privilege escalation attack vector | UI-only management (decided) |
| **Retrievable keys** | "I lost my key, show it again" | Forces plaintext or reversible encryption storage, major security risk | Show once only, user must regenerate |
| **Auto-generated names** | "Just give me a key fast" | Proliferation of unnamed keys, impossible to identify later | Require meaningful name on creation |
| **Mandatory expiration** | "Force rotation for security" | User friction, breaks automations silently, support burden | Optional expiration with reminders |
| **Key editing** | "Let me rename or extend expiration" | Complexity in audit trail, confusion about what key does | Create new key, revoke old one |
| **Shared team keys** | "My team needs the same key" | Attribution impossible, blast radius of leak includes all team usage | Per-user keys, team members create own |
| **Test button in UI** | "Let me verify my key works" | Creates API calls, edge cases with rate limits, partial testing | Documentation with curl examples |
| **Email notifications for expiry** | "Remind me before it expires" | Infrastructure complexity, spam concerns, users ignore emails | Dashboard warning banner |
| **Automatic key rotation** | "Rotate my keys automatically" | Breaks integrations silently, sync issues with client apps | Manual rotation with clear UI |
| **Real-time revocation propagation** | "Revoke should work instantly everywhere" | Distributed cache invalidation complexity | Accept ~1 minute propagation delay |

## Feature Dependencies

```
[Hash Storage]
    └──requires──> [Key Generation]
                       └──enables──> [Key Validation]

[Last Used Tracking] ──requires──> [Key Validation (fast lookup)]

[Per-Key Rate Limiting] ──requires──> [Key Validation]
                              └──requires──> [Redis Infrastructure] (existing)

[Key List View]
    └──requires──> [Key Creation]
    └──requires──> [Masked Display]

[Revocation] ──requires──> [Key List View]
         └──requires──> [Confirmation Dialog]

[Optional Expiration] ──enhances──> [Key Creation]
                          └──checked-during──> [Key Validation]

[Scoped Permissions v2] ──requires──> [Full Access v1 working]
                             └──requires──> [Permission Model]
                             └──requires──> [Scope Selection UI]
```

### Dependency Notes

- **Key Validation requires Hash Storage:** Must hash input key and compare to stored hash
- **Last Used Tracking requires fast validation:** Cannot add latency to every API call
- **Scoped Permissions blocked until v1 stable:** Ship full_access first, add granularity later
- **Per-key rate limiting requires key validation:** Must identify key before applying limit

## MVP Definition

### Launch With (v1)

Minimum viable product - what's needed to replace JWT auth for MCP clients.

- [x] Key creation with required name field - essential for identification
- [x] Prefixed key format (`och_live_...`) - industry standard, leak detection
- [x] Show full key once with copy button - security requirement
- [x] Masked display in list (last 4 chars) - security requirement
- [x] Key revocation with confirmation - essential lifecycle management
- [x] Hashed storage (SHA-256) - security requirement
- [x] Created timestamp display - basic metadata
- [x] Last used timestamp tracking - identifies active vs stale keys
- [x] Optional expiration date - user flexibility
- [x] Full access scope only - simplify v1
- [x] Dedicated API Keys navigation - discoverability
- [x] Backend supporting both JWT and API key auth - migration path
- [x] Per-key rate limiting - security isolation
- [x] Unlimited keys per user - no artificial friction

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Scoped permissions (read-only, write-only) - when users request granularity
- [ ] Dashboard warning for expiring keys - when expiration adoption increases
- [ ] Request count per key - when users ask "how much is this key used?"
- [ ] Audit logging - when compliance requirements emerge

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] IP allowlisting - significant complexity, wait for demand
- [ ] Key usage analytics dashboard - requires metrics infrastructure
- [ ] API management via REST - only if strong use case emerges, security tradeoff
- [ ] Team/organization keys - requires team model, attribution challenges

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Key creation + show once | HIGH | LOW | P1 |
| Copy-to-clipboard | HIGH | LOW | P1 |
| Masked display | HIGH | LOW | P1 |
| Key revocation | HIGH | LOW | P1 |
| Hashed storage | HIGH | MEDIUM | P1 |
| Last used tracking | MEDIUM | MEDIUM | P1 |
| Optional expiration | MEDIUM | LOW | P1 |
| Per-key rate limiting | MEDIUM | MEDIUM | P1 |
| Prefixed format | MEDIUM | LOW | P1 |
| Dedicated nav menu | MEDIUM | LOW | P1 |
| Scoped permissions | MEDIUM | HIGH | P2 |
| Audit logging | LOW | MEDIUM | P3 |
| IP allowlisting | LOW | HIGH | P3 |
| Usage analytics | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Stripe | GitHub | OpenAI | Our Approach |
|---------|--------|--------|--------|--------------|
| Prefixed keys | `sk_live_`, `pk_live_` | `ghp_`, `ghs_` | `sk-proj-` | `och_live_` |
| Show once only | Yes | Yes | Yes | Yes |
| Last used tracking | Yes | Yes | Yes | Yes |
| Revocation | Yes | Yes | Yes | Yes |
| Expiration | Optional | Configurable | No | Optional |
| Scoped permissions | Yes (restricted keys) | Yes (fine-grained) | Project-level | v1: full only, v2: scopes |
| IP restrictions | Yes | No | No | v2+ |
| Rate limiting per key | Yes | Yes | Per-project | Yes (per key) |
| REST API management | Yes | Yes | Yes | No (UI only - security) |
| Audit logging | Yes | Yes | Limited | v2+ |

## Security Considerations

### Hashing Strategy

- **Use SHA-256 for API keys** (not bcrypt) - API keys need fast validation (<50ms)
- **Store prefix + hash** - Enables masked display without decryption
- **Never store plaintext** - Hash immediately on creation

### Key Format

```
och_live_<32_random_chars>
^        ^
prefix   cryptographically secure random string
```

- Prefix enables: log scanning for leaked keys, immediate identification
- Random portion: 32 chars provides ~190 bits of entropy

### Validation Flow

```
1. Extract key from Authorization header
2. Parse prefix to identify key type
3. Hash the full key
4. Look up hash in database (indexed)
5. Check expiration if set
6. Update last_used timestamp (async)
7. Apply per-key rate limit
8. Proceed with request
```

## UX Patterns

### Key Creation Flow

1. User clicks "Create API Key"
2. Modal opens with:
   - Name field (required, placeholder: "Claude Desktop")
   - Expiration dropdown (Never, 30 days, 90 days, 1 year, Custom)
3. Submit creates key
4. Success modal shows:
   - Full key with monospace font
   - Copy button with "Copied!" feedback
   - Warning: "This is the only time you'll see this key"
   - "Done" button to close

### Key List View

| Name | Key | Created | Last Used | Expires | Actions |
|------|-----|---------|-----------|---------|---------|
| Claude Desktop | `och_live_****1234` | Jan 30, 2026 | 2 hours ago | Never | Revoke |
| CI Pipeline | `och_live_****5678` | Jan 15, 2026 | Never used | Mar 15, 2026 | Revoke |

### Revocation Flow

1. User clicks "Revoke" button
2. Confirmation modal:
   - Title: "Revoke API Key?"
   - Body: "This will permanently revoke 'Claude Desktop'. Any applications using this key will stop working immediately."
   - Actions: "Cancel" (secondary), "Revoke" (danger/red)
3. On confirm: key deleted, list refreshed

## Sources

### Security Best Practices
- [Google Cloud API Keys Best Practices](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices)
- [OpenAI API Key Safety Best Practices](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety)
- [API Key Security Best Practices - Legit Security](https://www.legitsecurity.com/aspm-knowledge-base/api-key-security-best-practices)
- [API Keys Weaknesses - TechTarget](https://www.techtarget.com/searchsecurity/tip/API-keys-Weaknesses-and-security-best-practices)

### UX Patterns
- [Carbon Design System - Generate API Key Pattern](https://carbondesignsystem.com/community/patterns/generate-an-api-key/)
- [Stripe API Keys Documentation](https://docs.stripe.com/keys)
- [Datadog API Key Management](https://docs.datadoghq.com/account_management/api-app-keys/)
- [Anthropic API Key Guide](https://docs.anthropic.com/en/api/admin-api/apikeys/get-api-key)

### Rate Limiting
- [API Rate Limiting Guide 2026 - Levo](https://www.levo.ai/resources/blogs/api-rate-limiting-guide-2026)
- [Azure API Management Rate Limit by Key](https://learn.microsoft.com/en-us/azure/api-management/rate-limit-by-key-policy)
- [Postman API Rate Limiting](https://blog.postman.com/what-is-api-rate-limiting/)

### Key Format Conventions
- [API Key Prefixes Best Practices - Mergify](https://articles.mergify.com/api-keys-best-practice/)
- [Designing Secure API Keys - Glama](https://glama.ai/blog/2024-10-18-what-makes-a-good-api-key)
- [Stripe Authentication Reference](https://docs.stripe.com/api/authentication)

---
*Feature research for: API Key Management*
*Researched: 2026-01-30*
