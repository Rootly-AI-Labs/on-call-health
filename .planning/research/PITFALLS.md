# Pitfalls Research: Adding API Token Support to OAuth Integrations

**Domain:** Dual authentication systems (OAuth + API tokens)
**Researched:** 2026-01-30
**Confidence:** HIGH

---

## Critical Pitfalls

### Pitfall 1: Inconsistent Token Storage Security

**What goes wrong:**
API tokens stored with weaker encryption or plaintext while OAuth tokens use proper encryption. This creates a security downgrade where adding "convenience" (API tokens) introduces vulnerabilities that didn't exist in the OAuth-only system.

**Why it happens:**
Developers assume API tokens are "simpler" and don't need the same security rigor as OAuth. The existing OAuth encryption infrastructure (Fernet with ENCRYPTION_KEY) may not be reused for API tokens, leading to ad-hoc storage solutions like environment variables or config files.

**Consequences:**
- Security audit fails because different credentials have different protection levels
- API token leaks expose the entire integration, not just a short-lived OAuth session
- Compliance violations (GDPR, SOC2) for inconsistent sensitive data handling
- Cannot prove to security teams that API tokens receive equivalent protection

**Prevention:**
- **MUST**: Reuse existing `encrypt_token()` and `decrypt_token()` functions from `integration_validator.py`
- **MUST**: Store API tokens in same database columns as OAuth tokens (`access_token` column with encryption)
- **MUST**: Use same `ENCRYPTION_KEY` from config for all credential types
- **VERIFY**: All token storage paths use `Fernet(get_encryption_key())` consistently
- **TEST**: Write security tests that verify API tokens are never stored in plaintext

**Warning signs:**
- API token storage code bypasses existing encryption helpers
- New database columns added without encryption layer
- Environment variables used to store user-provided API tokens
- Tests that mock encryption only for OAuth paths, not API token paths

**Phase to address:**
Phase 1: Token Storage Architecture - Establish encryption parity as first requirement before any API token input

---

### Pitfall 2: Confused Permission Scoping

**What goes wrong:**
OAuth tokens have scopes like `read:jira-work read:jira-user` while API tokens may have different, broader permissions (e.g., Jira API tokens have ALL permissions of the creating user). Code assumes all tokens have same permission boundaries, leading to over-privileged API operations.

**Why it happens:**
OAuth scopes are explicit in the authorization flow, but API token permissions are often:
- Determined by the creating user's role (not visible to your system)
- All-or-nothing rather than granular
- Not discoverable through API introspection

**Consequences:**
- Security incident: API token performs actions OAuth would reject
- Compliance violation: Users gain more access through "manual" path than OAuth
- Cannot implement least-privilege principle consistently
- Risk assessment becomes impossible (cannot predict what each token can do)

**Prevention:**
- **DESIGN**: Add `token_scopes` JSON column to store discovered/declared permissions
- **VALIDATION**: Test token permissions on setup with `test_permissions()` calls
- **DOCUMENTATION**: Warn users that API tokens may have broader access than OAuth
- **AUDIT**: Log which token type performed which operation for security review
- **FAIL SAFE**: If scope cannot be determined, assume broadest permissions and flag for review

**Warning signs:**
- Permission checks only validate for OAuth flows
- No capability testing during API token setup
- Code assumes `token_source == 'manual'` means limited access
- Error messages don't distinguish between OAuth scope denial vs API token permission denial

**Phase to address:**
Phase 1: Token Storage Architecture - Add permission metadata fields
Phase 2: Token Validation Logic - Implement scope checking before use

---

### Pitfall 3: No Expiration Strategy for API Tokens

**What goes wrong:**
OAuth tokens expire (Jira: 1hr, Linear: 24hr) and automatically refresh. API tokens have no expiration, creating infinite-lived credentials that violate security best practices. System never prompts users to rotate API tokens.

**Why it happens:**
API providers don't offer refresh tokens for API keys. Developers skip expiration handling entirely rather than implementing manual rotation workflows. The `token_expires_at` field gets set to `NULL` for API tokens without considering security implications.

**Consequences:**
- Compromised API token grants perpetual access until manually revoked
- Security audit fails: no credential rotation policy
- Cannot implement "break glass" scenarios where all credentials expire
- Lost/forgotten API tokens accumulate in database forever
- Compliance violations (many standards require periodic credential rotation)

**Prevention:**
- **POLICY**: Set virtual expiration (e.g., 90 days) for API tokens in `token_expires_at`
- **NOTIFICATION**: Email users 2 weeks before virtual expiration to rotate token
- **UI**: Show "Last verified" date and "Expires in X days" for API tokens
- **REVOCATION**: Automatically disable API token integrations after virtual expiration
- **RENEWAL**: Provide self-service flow to update expired API token (not re-auth)
- **MONITORING**: Alert on API tokens older than 180 days

**Warning signs:**
- `token_expires_at IS NULL` for token_source='manual'
- No scheduled jobs checking API token age
- No UI showing token age or expiration status
- Users surprised when "it just stopped working" after months of use

**Phase to address:**
Phase 2: Token Validation Logic - Implement virtual expiration checking
Phase 3: User Experience - Add UI for token age and rotation reminders

---

### Pitfall 4: Token Type Confusion in Validation Logic

**What goes wrong:**
Validation code attempts to refresh API tokens (which can't refresh) or skips OAuth token refresh (because generic "token exists" check passes). The `needs_refresh()` logic fails to distinguish between token types, causing either infinite refresh loops or stale OAuth tokens.

**Why it happens:**
Both token types stored in same `access_token` column. Code checks `if integration.has_token` without checking `if integration.supports_refresh`. The `needs_refresh()` function doesn't account for API tokens that never expire vs OAuth tokens that need proactive refresh.

**Consequences:**
- OAuth tokens expire mid-operation because refresh was skipped
- Error logs full of "cannot refresh token" for API tokens
- Race conditions where refresh attempt happens while API token is in use
- User sees "token expired" error for API token that shouldn't expire
- Distributed lock contention from unnecessary refresh attempts

**Prevention:**
- **VALIDATION**: Always check `integration.supports_refresh` before calling refresh
- **BRANCHING**: Separate code paths for OAuth vs API token validation
```python
if integration.is_oauth and integration.needs_refresh:
    await refresh_oauth_token(integration)
elif integration.is_manual:
    # API tokens don't refresh, check virtual expiration instead
    check_virtual_expiration(integration)
```
- **TESTING**: Write tests for both paths with proper mocking
- **LOGGING**: Log token type in all validation messages for debugging

**Warning signs:**
- Logs showing "refresh failed" for `token_source='manual'`
- OAuth tokens expiring despite refresh infrastructure
- Conditional logic like `if token_expires_at:` instead of `if is_oauth:`
- Generic exception handlers catching both OAuth and API token errors

**Phase to address:**
Phase 2: Token Validation Logic - Implement type-aware validation branching

---

### Pitfall 5: User Confusion - When to Use Which Method

**What goes wrong:**
Users don't understand when to use OAuth vs API token. They create API token thinking it's "easier" but then can't access certain features. Or they use OAuth but wanted the simplicity of API tokens. Support tickets increase, user frustration grows, adoption stalls.

**Why it happens:**
No clear guidance in UI about tradeoffs. Both options presented equally with generic "Choose authentication method" dropdown. Users pick based on what they see first, not what they need.

**Consequences:**
- Support burden: "Why can't I do X?" → "Because you chose API token"
- User abandonment: "This is too complicated" after choosing wrong method
- Security downgrade: Users pick API token to "avoid OAuth popup"
- Feature confusion: Capabilities differ by auth method but not documented
- Re-authentication churn: Users switch methods after initial setup

**Prevention:**
- **DECISION TREE**: Show comparison table before method selection
  - OAuth: Automatic renewal, secure, recommended for most users
  - API Token: Manual setup, for automation, requires rotation
- **USE CASE GUIDANCE**: "Use OAuth if: ...", "Use API Token if: ..."
- **WARNINGS**: "API tokens require manual rotation every 90 days"
- **CAPABILITY MATRIX**: Show which features work with which method
- **DEFAULT**: Pre-select OAuth unless user explicitly chooses API token
- **CONFIRMATION**: "You selected API token. This means..." before proceeding

**Warning signs:**
- Support tickets asking "what's the difference?"
- Users switching methods frequently
- High abandonment rate during authentication setup
- Users asking "which one should I pick?"

**Phase to address:**
Phase 3: User Experience - Add decision guidance UI
Phase 4: Documentation - Create comparison guide

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip token type validation during operations | Faster development, simpler code | Confusion errors, security incidents | Never - validation is critical |
| Store API tokens without encryption | Easier implementation | Security audit failure, compliance violation | Never - encryption is required |
| No virtual expiration for API tokens | Simpler token management | Perpetual credentials, security risk | Never - expiration policy required |
| Reuse OAuth refresh logic for API tokens | Less code duplication | Failed refresh attempts, error noise | Never - tokens need separate paths |
| Single "Add Integration" flow for both methods | Simpler UI | User confusion, wrong method selection | Only for MVP, must add guidance in Phase 2 |
| Generic error messages for both token types | Less error handling code | Debugging nightmares, user confusion | Never - errors must indicate token type |
| Assume API tokens have same scope as OAuth | Simplifies permission model | Security gaps, over-privileged operations | Never - scopes must be checked |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Jira API Token | Assuming token has same scopes as OAuth `read:jira-work` | Test permissions on setup - API token has ALL user permissions |
| Jira OAuth | Not handling 1-hour expiration aggressively | Refresh token when `expires_at - now < 5 minutes` |
| Linear API Token | Expecting refresh token like OAuth | API tokens are long-lived (no refresh), set virtual 90-day expiration |
| Linear OAuth | Assuming 1-hour expiration like Jira | Linear tokens last 24 hours, refresh when `< 1 hour` remaining |
| Both | Storing token_source after validation | Set token_source BEFORE first API call for proper error handling |
| Both | Using same HTTP headers for both methods | OAuth: `Authorization: Bearer <token>`, API tokens vary by provider |
| Jira | Expecting API token to work with cloud_id | API tokens are per-user, still need cloud_id from accessible_resources |
| Linear | Treating API token as OAuth access_token | API tokens don't have associated refresh_token or expires_at |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Refresh all OAuth tokens on cron job | High database load at same time | Randomize refresh time per integration | >100 integrations |
| Check token expiration on every API call | Latency spikes, DB connection pool exhaustion | Cache expiration check for 1 minute | >1000 API calls/minute |
| Attempt refresh on first API failure | Cascading failures, timeout storms | Proactive refresh before expiration | >50 concurrent users |
| Encrypt/decrypt on every token read | CPU spikes, slow API responses | Cache decrypted token in request context | >500 requests/minute |
| Sequential permission testing during setup | Slow onboarding, user abandonment | Parallel permission checks with timeout | >5 permission tests |
| Lock entire table during token refresh | Other users blocked waiting | Use row-level or distributed locks (Redis) | >10 concurrent refreshes |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| Log decrypted tokens in error messages | Token leakage in logs, SIEM systems | Always log `token[:8]...` not full token |
| Store encryption key in application code | Source code leak exposes all tokens | Use environment variable, never commit |
| Same encryption key for JWT and token storage | Key compromise affects both auth systems | Use separate `JWT_SECRET_KEY` and `ENCRYPTION_KEY` |
| API token sent in URL query parameters | Token in browser history, proxy logs | Always use Authorization header or POST body |
| Allow API token in webhook callbacks | Token exposed to third-party servers | Webhooks should use HMAC signing, not bearer tokens |
| Skip TLS certificate validation in dev | Dev-to-production config leak disables TLS | Always validate certificates, use test certs in dev |
| Reuse OAuth state parameter | CSRF vulnerability in token exchange | Generate unique state per authorization flow |
| Store token_source based on user input | User claims "OAuth" but provides API token | Determine token_source by attempting introspection |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| "Authentication method" dropdown with no explanation | Users guess, pick wrong method, get frustrated | Show decision tree with "Recommended" badge on OAuth |
| Generic "Token invalid" error | User doesn't know if OAuth expired or API token wrong | "Your OAuth token expired. Click to reconnect" vs "API token authentication failed. Check token in Jira settings" |
| No indication which integration uses which method | User forgets what they set up 3 months ago | Show badge: "OAuth (Auto-renew)" vs "API Token (Rotate by Feb 1)" |
| Setup flow doesn't test token immediately | User completes setup, integration fails later | Test permissions during setup, show what works/doesn't |
| Can't switch from API token to OAuth without re-setup | User realizes they want auto-renewal | "Upgrade to OAuth" button that migrates integration |
| No reminder when API token approaching expiration | Integration suddenly stops working | Email user 2 weeks before virtual expiration |
| Error says "reconnect" for both token types | User goes through OAuth flow for API token issue | "Update API token" vs "Reconnect OAuth" |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **API Token Storage:** Token encryption uses same key/algorithm as OAuth—verify `encrypt_token()` function reused
- [ ] **Token Refresh Logic:** Code checks `integration.supports_refresh` before attempting refresh—verify no refresh attempts for `token_source='manual'`
- [ ] **Expiration Handling:** API tokens have virtual expiration set in `token_expires_at`—verify not NULL for manual tokens
- [ ] **Permission Testing:** Setup flow calls `test_permissions()` for API tokens—verify capabilities stored in metadata
- [ ] **Scope Validation:** Operations check token capabilities before execution—verify both OAuth scopes AND API token permissions validated
- [ ] **Error Messages:** Errors distinguish between OAuth and API token issues—verify token_source included in error context
- [ ] **UI Guidance:** Setup page explains OAuth vs API token tradeoffs—verify decision tree or comparison table present
- [ ] **Rotation Reminders:** Scheduled job checks API token age—verify notification sent before virtual expiration
- [ ] **Audit Logging:** Token operations log token_source and scope—verify can trace which token performed which action
- [ ] **Migration Path:** Users can upgrade from API token to OAuth—verify state preserved during method change
- [ ] **Documentation:** Setup guide covers both methods with recommendations—verify troubleshooting for each type
- [ ] **Security Tests:** Tests verify API tokens encrypted—verify no plaintext tokens in database dumps

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| API tokens stored without encryption | HIGH | 1. Generate new ENCRYPTION_KEY, 2. Email all users to re-enter API tokens, 3. Encrypt new tokens, 4. Rotate old tokens as users update |
| OAuth and API tokens have inconsistent scopes | MEDIUM | 1. Add permission metadata to all integrations, 2. Test existing tokens, 3. Flag over-privileged API tokens, 4. Notify users of changes |
| API tokens never expire (no rotation policy) | MEDIUM | 1. Set virtual expiration dates retroactively, 2. Email users with rotation deadlines, 3. Implement rotation reminders |
| Token validation doesn't check token_source | LOW | 1. Add type-aware validation, 2. Deploy with feature flag, 3. Monitor error rates, 4. Enable for all users |
| Users confused about OAuth vs API token | LOW | 1. Add decision tree to setup UI, 2. Email existing users with guidance, 3. Offer migration tool |
| Logs contain decrypted tokens | HIGH | 1. Rotate all potentially leaked tokens, 2. Fix logging code, 3. Purge old logs, 4. Implement log scrubbing |
| No virtual expiration for API tokens | MEDIUM | 1. Set expiration policy (90 days), 2. Backfill expiration dates, 3. Add rotation reminders, 4. Email users before first expiration wave |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Inconsistent token storage security | Phase 1: Token Storage Architecture | Test that both OAuth and API tokens use same encryption; database dump shows no plaintext |
| Confused permission scoping | Phase 1: Storage + Phase 2: Validation | Permission metadata stored; test_permissions() called during setup |
| No expiration strategy for API tokens | Phase 2: Token Validation Logic | Virtual expiration set; scheduled job checks token age |
| Token type confusion in validation | Phase 2: Token Validation Logic | Separate code paths for OAuth vs API; no refresh attempts for manual tokens |
| User confusion about methods | Phase 3: User Experience | Decision tree in UI; comparison table shown before selection |
| No rotation reminders | Phase 3: UX + Phase 5: Monitoring | Email sent 2 weeks before expiration; UI shows expiration date |
| Generic error messages | Phase 3: User Experience | Errors mention token type; different messages for OAuth vs API issues |
| Performance at scale | Phase 4: Optimization (future) | Token caching; distributed locks; parallel permission tests |
| Audit/compliance gaps | Phase 5: Monitoring & Security | Audit logs show token_source; security tests verify encryption |

---

## Sources

- [API Keys vs OAuth: Which API Authentication Method Is More Secure? - Security Boulevard](https://securityboulevard.com/2026/01/api-keys-vs-oauth-which-api-authentication-method-is-more-secure/)
- [API Authentication Best Practices in 2026 - DEV Community](https://dev.to/apiverve/api-authentication-best-practices-in-2026-3k4a)
- [OAuth 2.0 for APIs: Flows, Tokens, and Pitfalls - Treblle](https://treblle.com/blog/oauth-2.0-for-apis)
- [The State of API Security in 2026: Common Misconfigurations and Exploitation Vectors](https://www.appsecure.security/blog/state-of-api-security-common-misconfigurations)
- [API Security Best Practices for API keys and tokens](https://42crunch.com/token-management-best-practices/)
- [API Keys vs OAuth - Discover Best Practices to Secure your APIs](https://blog.axway.com/learning-center/digital-security/keys-oauth/api-keys-oauth)
- [When JIRA Security is Top Priority: Best Practices to Learn From](https://nordlayer.com/blog/jira-security-best-practices/)
- [Remediating Jira API Token leaks | GitGuardian](https://www.gitguardian.com/remediation/jira-api-token)
- [Manage API tokens for your Atlassian account | Atlassian Support](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)
- [OAuth 2.0 authentication – Linear Developers](https://linear.app/developers/oauth-2-0-authentication)
- [Linear API Essentials](https://rollout.com/integration-guides/linear/api-essentials)
- [Remediating Linear Personal API key leaks | GitGuardian](https://www.gitguardian.com/remediation/linear-personal-api-key)
- [OAuth Scopes Best Practices | Curity](https://curity.io/resources/learn/scope-best-practices/)
- [Understanding the differences between API tokens and OAuth access tokens | Zendesk Developer Docs](https://developer.zendesk.com/documentation/api-basics/authentication/oauth-vs-api-tokens/)
- [UX best practices for MFA — WorkOS](https://workos.com/blog/ux-best-practices-for-mfa)
- [Multi factor authentication design: Security meets usability in UI/UX design - LogRocket Blog](https://blog.logrocket.com/ux-design/authentication-ui-ux/)
- [JWT Security Best Practices: Checklist for APIs | Curity](https://curity.io/resources/learn/jwt-best-practices/)
- [Validate Access Tokens | Okta Developer](https://developer.okta.com/docs/guides/validate-access-tokens/dotnet/main/)

---

*Pitfalls research for: Token-based authentication (OAuth + API tokens) in On-Call Health platform*
*Researched: 2026-01-30*
