# Project Research Summary

**Project:** Token-Based Authentication for Jira and Linear Integrations
**Domain:** Dual authentication systems (OAuth 2.0 + API tokens)
**Researched:** 2026-01-30
**Confidence:** HIGH

## Executive Summary

This project extends the existing OAuth-based Jira and Linear integrations to support manual API token authentication alongside the existing OAuth flows. This dual-auth pattern addresses users blocked by enterprise OAuth policies while maintaining the existing OAuth experience for users who prefer it. Research shows this is a well-established pattern in 2026, with clear architectural approaches and documented pitfalls.

The recommended approach leverages existing infrastructure: reuse the current encryption system (Fernet with ENCRYPTION_KEY), add a discriminator field (token_source) to existing integration models, and create a token abstraction layer that hides OAuth refresh logic from API clients. The codebase already has strong patterns from Rootly/PagerDuty token-based integrations that can be extended to Jira/Linear. Critical architectural decision: use a single integration table per provider rather than separate tables for OAuth vs manual tokens—this simplifies queries, enables method switching, and avoids data duplication.

The primary risk is inconsistent security between OAuth and API tokens—specifically, developers might skip the existing encryption infrastructure for "simpler" API tokens, creating a security downgrade. Secondary risks include token type confusion in validation logic (attempting to refresh non-refreshable API tokens) and user confusion about when to use which method. Mitigation requires: (1) establishing encryption parity in Phase 1 before any token input, (2) type-aware validation branching in Phase 2, and (3) clear UX guidance in Phase 3 with decision trees showing OAuth as recommended default.

## Key Findings

### Recommended Stack

All necessary technologies are already in the project—no new packages required. The existing cryptography (46.0.4), httpx, pydantic, SQLAlchemy, and PostgreSQL stack provides everything needed for dual authentication.

**Core technologies:**
- **cryptography (Fernet)**: Token encryption/decryption using same AES-128-CBC + HMAC as existing OAuth tokens—critical for security parity
- **httpx AsyncClient**: API validation for both Jira Basic Auth and Linear Bearer tokens—already used in integration_validator.py
- **SQLAlchemy with discriminator pattern**: Single integration table with token_source field ('oauth' | 'manual')—avoids data duplication
- **base64 (stdlib)**: Jira API tokens require HTTP Basic Auth with base64-encoded "email:api_token" format
- **PostgreSQL**: Existing jira_integrations and linear_integrations tables already support manual tokens via token_source field

**Critical version notes:**
- Jira API tokens expire in 1 year by default (March-May 2026 batch approaching)
- Linear API keys never expire unless manually revoked
- OAuth tokens: Jira 1-hour expiry, Linear 24-hour expiry
- cryptography 46.0.4 is latest stable (Jan 2026), supports free-threaded Python 3.14

### Expected Features

**Must have (table stakes):**
- Authentication Method Selection — users need to choose between OAuth and API token upfront
- Token Validation on Setup — real-time validation after field completion prevents broken integrations
- Clear Error Messaging — specific, actionable errors distinguishing OAuth expiry vs invalid API token
- Visual Status Indicators — badges showing "Connected - OAuth" vs "Connected - API Token"
- Token Security Warnings — clear disclosure about encryption and data access during setup
- Connection Testing — verify token works before saving integration

**Should have (competitive advantages):**
- Seamless Method Switching — disconnect OAuth and reconnect with token without losing integration history
- Permission Scope Preview — show exactly what permissions token grants before connection
- Duplicate Token Detection — prevent same token being added multiple times (already implemented for Rootly/PagerDuty)

**Defer (v2+):**
- Expiry Proactive Notifications — notify users 30 days and 7 days before token expires (defer until 100+ token-based integrations)
- Token Health Dashboard — centralized view of all integration token status (defer until users manage 5+ integrations)
- Automatic Token Refresh Detection — badge showing OAuth supports refresh vs tokens need manual rotation (defer until refresh issues arise)

### Architecture Approach

Dual-auth systems separate authentication method from authorization logic using three key patterns: (1) Strategy Pattern for token retrieval with get_valid_token() abstraction that handles OAuth refresh vs manual tokens, (2) Discriminator Field Pattern with single integration table and token_source field to differentiate OAuth vs manual, and (3) Unified Validation Interface that validates all integrations identically regardless of auth source.

**Major components:**
1. **Token Abstraction Layer (token_manager.py)** — provides get_valid_token() that hides OAuth refresh logic; API clients don't care about token source
2. **Manual Token Endpoints** — new routes like /jira/manual/setup and /linear/manual/setup for accepting user-provided API tokens with immediate validation
3. **Integration Models with Discriminator** — existing jira_integrations and linear_integrations tables extended with token_source field; refresh_token nullable for manual tokens
4. **Unified Validator** — existing integration_validator.py extended to handle both OAuth (with refresh) and manual (without refresh) validation paths
5. **Frontend UI Separation** — separate setup components (OAuth redirect flow vs manual form) but shared status display components

**Recommended structure:**
- Separate API route files for OAuth vs manual (jira.py + jira_manual.py)
- Single integration model per provider with token_source discriminator
- Centralized encryption utilities in core/encryption.py
- Token abstraction layer in services/token_manager.py
- Frontend: separate setup UIs, shared status badges

### Critical Pitfalls

1. **Inconsistent Token Storage Security** — API tokens stored with weaker encryption or plaintext while OAuth tokens use proper encryption. MUST reuse existing encrypt_token()/decrypt_token() functions from integration_validator.py and same ENCRYPTION_KEY for all credential types. Verify with security tests that API tokens never stored in plaintext.

2. **Confused Permission Scoping** — OAuth tokens have explicit scopes (read:jira-work) while API tokens may have ALL permissions of creating user. Code assumes both have same boundaries. Add token_scopes JSON column, test permissions during setup with test_permissions() calls, document that API tokens may have broader access than OAuth.

3. **No Expiration Strategy for API Tokens** — OAuth tokens expire and auto-refresh; API tokens have no expiration, creating infinite-lived credentials. Set virtual expiration (90 days) in token_expires_at even for manual tokens, email users 2 weeks before virtual expiration to rotate, provide self-service renewal flow.

4. **Token Type Confusion in Validation Logic** — validation code attempts to refresh API tokens (which can't refresh) or skips OAuth refresh. Always check integration.supports_refresh before calling refresh. Use separate code paths: if integration.is_oauth and integration.needs_refresh then refresh, elif integration.is_manual then check_virtual_expiration().

5. **User Confusion - When to Use Which Method** — users don't understand tradeoffs between OAuth and API token. Show comparison table before method selection, pre-select OAuth as recommended, add confirmation dialog explaining implications of API token choice (manual rotation required, broader permissions).

## Implications for Roadmap

Based on research, suggested phase structure emphasizes early security foundation and incremental feature addition:

### Phase 1: Token Storage Architecture & Data Model
**Rationale:** Must establish encryption parity and data model before accepting any user-provided tokens. Critical pitfall prevention phase—if token storage security is inconsistent from the start, requires HIGH-cost recovery (re-encrypt all tokens, force user rotation). Foundation enables all subsequent phases.

**Delivers:**
- Database migration adding token_source field to jira_integrations and linear_integrations
- Model properties: is_oauth, is_manual, supports_refresh
- Token abstraction layer (TokenManager service with get_valid_token() method)
- Encryption parity verification tests

**Addresses:**
- Pitfall #1 (Inconsistent Token Storage Security)
- Pitfall #2 setup (Confused Permission Scoping - add metadata fields)

**Avoids:** Security downgrade from day one; technical debt that's expensive to fix later

### Phase 2: Manual Token Input & Validation
**Rationale:** Once storage is secure, build token acceptance endpoints. This phase implements the core value prop—let users provide API tokens when OAuth is blocked. Includes immediate validation to prevent broken integrations. Depends on Phase 1's TokenManager abstraction.

**Delivers:**
- Backend endpoints: POST /jira/manual/setup, POST /linear/manual/setup
- Token validation logic with type-aware branching (OAuth refresh vs manual virtual expiration)
- Permission testing during setup (test_permissions() calls)
- Virtual expiration policy (90 days for manual tokens)

**Uses:**
- Fernet encryption (STACK.md)
- httpx for API validation (STACK.md)
- base64 for Jira Basic Auth encoding (STACK.md)

**Implements:**
- Manual Token Endpoints component (ARCHITECTURE.md)
- Unified Validation Interface extension (ARCHITECTURE.md)

**Addresses:**
- Authentication Method Selection feature (FEATURES.md - must have)
- Token Validation on Setup feature (FEATURES.md - must have)
- Connection Testing feature (FEATURES.md - must have)

**Avoids:**
- Pitfall #4 (Token Type Confusion in Validation Logic)
- Pitfall #3 (No Expiration Strategy for API Tokens)

### Phase 3: Frontend UI & User Experience
**Rationale:** With backend complete, build user-facing setup flows. Critical for adoption—users must understand when to use OAuth vs API token. Includes decision guidance to prevent method confusion and support burden.

**Delivers:**
- Manual token input forms (JiraManualSetup.tsx, LinearManualSetup.tsx)
- Authentication method selection UI with decision tree
- Visual status indicators showing "OAuth (Auto-renew)" vs "API Token (Rotate by...)"
- Clear error messaging distinguishing OAuth vs manual token issues
- Token security warnings and setup help text

**Addresses:**
- Visual Status Indicators feature (FEATURES.md - must have)
- Clear Error Messaging feature (FEATURES.md - must have)
- Token Security Warnings feature (FEATURES.md - must have)

**Avoids:**
- Pitfall #5 (User Confusion - When to Use Which Method)
- UX pitfall: generic errors that don't distinguish token types
- UX pitfall: no indication which integration uses which method

### Phase 4: Method Switching & Polish (v1.x)
**Rationale:** Add after MVP validation. Users will request "I want to switch from OAuth to token" once they understand the options. Not blocking for initial launch but important for retention.

**Delivers:**
- Seamless method switching (maintain integration history when changing auth)
- Permission scope preview during token setup
- Duplicate token detection (extend existing Rootly/PagerDuty pattern)
- Documentation and troubleshooting guides

**Addresses:**
- Seamless Method Switching feature (FEATURES.md - differentiator)
- Permission Scope Preview feature (FEATURES.md - differentiator)
- Duplicate Token Detection feature (FEATURES.md - should have)

### Phase 5: Monitoring & Proactive Management (v2)
**Rationale:** Defer until scale demands it (100+ token integrations or 30%+ token adoption). Requires infrastructure investment (notification system, scheduled jobs, health dashboard) not justified for small user base.

**Delivers:**
- Expiry proactive notifications (email 30 days and 7 days before expiration)
- Token health dashboard (centralized view of all integration status)
- Automated token age monitoring and alerts
- Audit logging for compliance

**Addresses:**
- Expiry Proactive Notifications feature (FEATURES.md - defer v2+)
- Token Health Dashboard feature (FEATURES.md - defer v2+)

### Phase Ordering Rationale

- **Phase 1 first:** Security foundation must be established before accepting any user credentials. Fixing encryption inconsistency later requires HIGH-cost recovery (force token rotation). Token abstraction layer enables all subsequent validation logic.

- **Phase 2 before Phase 3:** Backend must exist before frontend can use it. Also, backend validation logic is testable independently—can verify token encryption, validation branching, and virtual expiration without UI.

- **Phase 3 critical for adoption:** Even with perfect backend, users won't adopt without clear UI guidance. Decision tree prevents "wrong method" support burden. Error messaging differentiation reduces confusion.

- **Phase 4 after MVP validation:** Method switching is valuable but not launch-blocking. Defer until users actually request it (trigger: 5+ users ask to switch). Avoids premature complexity.

- **Phase 5 at scale:** Notification infrastructure overhead not justified until meaningful token adoption. Trigger: 100+ token integrations OR 3+ expirations causing user pain.

**Dependency chain:**
```
Phase 1 (Storage) → Phase 2 (Validation) → Phase 3 (UI) → Phase 4 (Polish) → Phase 5 (Scale)
     ↓                    ↓                      ↓
  Data model    Token acceptance      User-facing flows
  Encryption    Type-aware logic      Decision guidance
  Abstraction   Virtual expiration    Status display
```

### Research Flags

**Phases likely needing deeper research during planning:**
- **Phase 2:** May need research on Jira CAPTCHA protection if validation failures trigger lockouts (mentioned in STACK.md source). Pattern: "Check for X-Seraph-LoginReason: AUTHENTICATION_DENIED header."
- **Phase 5:** May need research on notification infrastructure if not already in codebase. Need to verify if email system exists for proactive notifications.

**Phases with standard patterns (skip research-phase):**
- **Phase 1:** Data model extension is standard SQLAlchemy migration. Encryption pattern already exists in codebase (integration_validator.py encrypt_token/decrypt_token).
- **Phase 3:** Frontend form/modal patterns already established in jira-integration-card.tsx and integration-handlers.ts. Extend existing patterns.
- **Phase 4:** Method switching and duplicate detection patterns already exist for Rootly/PagerDuty integrations (integration-handlers.ts lines 7-105). Adapt existing code.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies already in requirements.txt. No new packages needed. Versions verified from PyPI (Jan 2026). Existing patterns in integration_validator.py and integration_oauth.py provide implementation reference. |
| Features | HIGH | Feature requirements validated against current industry standards (GitHub, GitLab, Atlassian products all support dual auth). MVP feature set matches existing token-based integrations in codebase (Rootly/PagerDuty). Competitive analysis confirms standard expectations. |
| Architecture | HIGH | Architecture patterns verified with FastAPI dual auth implementations (GitHub #1550), codebase already has discriminator field pattern (token_source in models), and token abstraction layer is standard Strategy Pattern. Build order dependencies clearly defined. |
| Pitfalls | HIGH | All five critical pitfalls validated with security sources (API Keys vs OAuth security research, JWT best practices, token management standards). Codebase inspection confirms encryption patterns must be preserved. UX pitfalls verified against authentication flow research. |

**Overall confidence:** HIGH

All research backed by official documentation (Jira Basic Auth docs, Linear API docs, FastAPI security docs, cryptography library docs) and verified against existing codebase patterns. No speculative recommendations—all suggestions either already proven in this codebase (Rootly/PagerDuty token flow) or standard patterns with documented implementations (Strategy Pattern for token retrieval).

### Gaps to Address

**Minor gap - Jira CAPTCHA handling:** STACK.md mentions Jira triggers CAPTCHA after multiple failed auth attempts. Need to verify during Phase 2 implementation whether existing validation cache (validation_cache.py with Redis) sufficiently rate-limits to prevent CAPTCHA trigger. If not, add retry limits before calling Jira API.

**Minor gap - Token expiration dates:** Linear API keys never expire, but Jira API tokens default to 1-year expiration. Need to verify during Phase 2 whether Jira API returns expiration date in token metadata or if we must set virtual 1-year expiration based on creation date. This affects token_expires_at field population.

**Minor gap - Permission introspection:** Research indicates API tokens may have broader permissions than OAuth scopes, but doesn't specify if Jira/Linear APIs provide introspection endpoints to list token permissions. During Phase 2, may need to test permissions empirically (try accessing resources) rather than query permission metadata. Validate this during initial implementation.

**No blocking gaps:** All core technical decisions (encryption, storage, validation) have clear patterns. Gaps above are implementation details resolvable during Phase 2 development.

## Sources

### Primary (HIGH confidence)
- [Jira Basic Auth for REST APIs](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/) — Jira API token authentication requirements, official mandated format
- [Manage API tokens for your Atlassian account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) — Jira API token expiration policy (1 year default)
- [Linear Getting Started](https://linear.app/developers/graphql) — Linear authentication methods, API key vs OAuth differences
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) — FastAPI dual auth patterns, security dependency injection
- [Fernet Symmetric Encryption](https://cryptography.io/en/latest/fernet/) — cryptography library implementation details, AES-128-CBC + HMAC
- [cryptography 46.0.4 on PyPI](https://pypi.org/project/cryptography/) — Latest stable version verification (Jan 2026)
- Existing codebase patterns — integration_validator.py, integration_oauth.py, jira-integration-card.tsx, integration-handlers.ts

### Secondary (MEDIUM confidence)
- [Curity: Token Patterns](https://curity.io/resources/learn/token-patterns/) — Token abstraction layer patterns
- [Auth0: Why Migrate from API Keys to OAuth2](https://auth0.com/blog/why-migrate-from-api-keys-to-oauth2-access-tokens/) — Dual authentication rationale
- [OAuth 2.0 for APIs: Flows, Tokens, and Pitfalls](https://treblle.com/blog/oauth-2.0-for-apis) — Common OAuth pitfalls, security best practices
- [API Security Best Practices 2026](https://42crunch.com/token-management-best-practices/) — Token lifecycle management, rotation policies
- [API Keys vs OAuth Security](https://securityboulevard.com/2026/01/api-keys-vs-oauth-which-api-authentication-method-is-more-secure/) — Security comparison, when to use each method
- [Jira API Token Best Practices](https://community.atlassian.com/forums/Jira-questions/User-API-Token-Best-Practices/qaq-p/3095043) — Community security guidance, expiration handling

### Tertiary (contextual)
- [The New Way To Generate Secure Tokens in Python](https://blog.miguelgrinberg.com/post/the-new-way-to-generate-secure-tokens-in-python) — Python secrets module (used for test token generation only)
- [OAuth Scopes Best Practices](https://curity.io/resources/learn/scope-best-practices/) — Permission scoping guidance
- [Linear API Essentials](https://rollout.com/integration-guides/linear/api-essentials) — Linear API token usage patterns

---
*Research completed: 2026-01-30*
*Ready for roadmap: yes*
