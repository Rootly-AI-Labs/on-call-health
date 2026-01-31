# Feature Research: Token-Based Authentication

**Domain:** Authentication method selection and switching for third-party integrations
**Researched:** 2026-01-30
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Authentication Method Selection** | Users need to choose between OAuth and API token upfront | LOW | Present both options in connection modal with clear labels. Industry standard pattern - see GitHub, GitLab, Atlassian products |
| **Token Validation on Setup** | Users expect immediate feedback if token is invalid | MEDIUM | Real-time validation after field completion prevents failed connections. Must validate format, permissions, and connectivity. Test endpoint pattern already implemented for Rootly/PagerDuty |
| **Clear Error Messaging** | Users need to understand why authentication failed | LOW | Provide specific, actionable error messages (invalid format, insufficient permissions, network error). Already implemented pattern in integration-handlers.ts |
| **Visual Status Indicators** | Users need to see connection health at a glance | LOW | Badge showing "Connected", connection method (OAuth vs Token), and expiry warnings. Already implemented in jira-integration-card.tsx |
| **Token Security Warnings** | Users need to understand token storage security | LOW | Clear disclosure about encryption, scope, and data access during setup. Trust-building essential for adoption |
| **Connection Testing** | Users expect to verify connection works before saving | MEDIUM | Test button that validates permissions and shows preview data. Already implemented for token-based Rootly/PagerDuty |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Seamless Method Switching** | Disconnect OAuth and reconnect with token without data loss | MEDIUM | Maintains integration history and settings when switching auth methods. QuickBooks announced this pattern for 2026 - becoming expected |
| **Permission Scope Preview** | Show exactly what permissions token grants before connection | MEDIUM | Display preview of accessible resources (sites, projects, users) before final connection. Builds trust and prevents scope surprises |
| **Automatic Token Refresh Detection** | Identify if token supports auto-refresh vs manual rotation | LOW | Badge/indicator showing OAuth supports refresh vs tokens need manual rotation. Sets proper expectations for maintenance |
| **Expiry Proactive Notifications** | Notify users 30 days and 7 days before token expires | MEDIUM | Industry standard timing (Intuit 2026 policy). Reduces integration failures from expired credentials |
| **Duplicate Token Detection** | Prevent same token being added multiple times | LOW | Already implemented in integration-handlers.ts. Prevents configuration errors and user confusion |
| **Token Health Dashboard** | Show token status across all integrations in one view | MEDIUM | Centralized view of expiry dates, last used, permission changes. Reduces maintenance burden for users with many integrations |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **Token Auto-Generation** | "Make it easier - generate token for me" | Violates OAuth security model, requires user credentials, massive security risk | Provide clear documentation links to create tokens in each platform (Jira, Linear, etc.) |
| **Store Token Client-Side** | "Keep it in browser for convenience" | LocalStorage/SessionStorage vulnerable to XSS attacks. API tokens must be server-side encrypted | Always store tokens server-side with AES-256 encryption (current pattern) |
| **Skip Token Validation** | "Let me save invalid token to fix later" | Creates broken integrations, confusing error states, support burden | Require validation before save. Show clear error preventing save until valid |
| **Automatic Method Migration** | "Auto-switch OAuth users to tokens when OAuth fails" | Users lose consent context, unclear what changed, breaks audit trail | Notify users OAuth failed, guide them to explicitly choose token method |
| **Token Sharing Between Teams** | "Share one token across workspace for easier management" | Token tied to user identity, breaks audit trail, permission scope confusion | Each user/integration needs own token. Document admin token for service accounts |
| **Permanent Tokens by Default** | "Never make me rotate tokens" | Security risk - compromised tokens remain valid indefinitely. Contradicts 2026 best practices | Encourage time-limited tokens, show warnings for permanent tokens, notify before expiry |

## Feature Dependencies

```
[Authentication Method Selection]
    └──requires──> [Token Validation on Setup]
                       └──requires──> [Clear Error Messaging]
                       └──requires──> [Connection Testing]

[Seamless Method Switching]
    └──requires──> [Token Validation on Setup]
    └──requires──> [Connection Testing]

[Expiry Proactive Notifications]
    └──requires──> [Token Health Dashboard]
    └──enhances──> [Visual Status Indicators]

[Permission Scope Preview]
    └──requires──> [Token Validation on Setup]
    └──conflicts──> [Skip Token Validation] (anti-feature)

[Token Security Warnings] ──enhances──> [Authentication Method Selection]

[Automatic Token Refresh Detection] ──enhances──> [Visual Status Indicators]
```

### Dependency Notes

- **Authentication Method Selection requires Token Validation**: Cannot offer token option without validating tokens work
- **Seamless Method Switching requires Connection Testing**: Must verify new auth method works before disconnecting old one
- **Expiry Notifications require Health Dashboard**: Need centralized tracking to send timely notifications
- **Permission Preview enhances Security Warnings**: Showing actual permissions makes security warnings concrete
- **Refresh Detection enhances Status**: Knowing refresh capability informs maintenance expectations

## MVP Definition

### Launch With (v1)

Minimum viable product - what's needed to unblock users who can't use OAuth.

- [x] **Authentication Method Selection** - Core value: let users choose OAuth or token
- [x] **Token Validation on Setup** - Prevent broken integrations from invalid tokens
- [x] **Clear Error Messaging** - Users must understand what went wrong to fix it
- [x] **Visual Status Indicators** - Show which auth method is connected at a glance
- [x] **Token Security Warnings** - Build trust by being transparent about security
- [x] **Connection Testing** - Verify token works before saving integration

**Why these six features**: This is the minimum to safely offer token authentication as an alternative to OAuth. All six already have patterns in the codebase (Rootly/PagerDuty token flow, Jira OAuth flow). Combining patterns = MVP.

### Add After Validation (v1.x)

Features to add once core token flow is working and users adopt it.

- [ ] **Seamless Method Switching** - Add when users request "I want to switch from OAuth to token"
  - Trigger: 5+ users request method switching
  - Risk if missing: Users disconnect and lose integration history

- [ ] **Permission Scope Preview** - Add when users report "token didn't have right permissions"
  - Trigger: 3+ support tickets about insufficient permissions
  - Risk if missing: Trial-and-error token creation experience

- [ ] **Duplicate Token Detection** - Already implemented for Rootly/PagerDuty, extend to Jira/Linear
  - Trigger: Immediate - code exists, just needs extension
  - Risk if missing: User confusion with duplicate integrations

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] **Expiry Proactive Notifications** - Defer until we have 100+ token-based integrations
  - Why defer: Notification infrastructure overhead not justified for small user base
  - Build when: 30%+ of integrations use tokens, OR 3+ expirations cause user pain

- [ ] **Token Health Dashboard** - Defer until users manage 5+ integrations per account
  - Why defer: Single integration view sufficient for most users initially
  - Build when: Average integrations per user > 3

- [ ] **Automatic Token Refresh Detection** - Defer until OAuth refresh issues arise
  - Why defer: Most API tokens don't expire (Jira, Linear tokens are permanent unless revoked)
  - Build when: Platform changes token policies (like Intuit 2026 changes)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Authentication Method Selection | HIGH | LOW | P1 |
| Token Validation on Setup | HIGH | MEDIUM | P1 |
| Clear Error Messaging | HIGH | LOW | P1 |
| Visual Status Indicators | HIGH | LOW | P1 |
| Token Security Warnings | HIGH | LOW | P1 |
| Connection Testing | HIGH | MEDIUM | P1 |
| Duplicate Token Detection | MEDIUM | LOW | P2 |
| Seamless Method Switching | MEDIUM | MEDIUM | P2 |
| Permission Scope Preview | MEDIUM | MEDIUM | P2 |
| Automatic Token Refresh Detection | LOW | LOW | P2 |
| Expiry Proactive Notifications | MEDIUM | HIGH | P3 |
| Token Health Dashboard | LOW | HIGH | P3 |

**Priority key:**
- P1: Must have for launch - blocks users from using token auth
- P2: Should have, add when user feedback indicates need
- P3: Nice to have, future consideration when scale demands it

## Competitor Feature Analysis

| Feature | Jira Cloud | Linear | GitLab | Our Approach |
|---------|------------|--------|--------|--------------|
| **OAuth Option** | Yes (OAuth 2.0 3LO) | Yes (OAuth 2.0) | Yes (OAuth 2.0) | Already implemented |
| **API Token Option** | Yes (Personal Access Tokens, API tokens) | Yes (API keys) | Yes (Personal Access Tokens) | Add to Jira/Linear integration modals |
| **Method Shown Together** | Separate flows, different docs | Separate flows | Both in same integration settings | Show both options in modal (differentiator) |
| **Token Validation** | Basic format validation | Server-side validation | Real-time validation | Real-time validation with preview (already have pattern) |
| **Permission Preview** | Shows scopes in OAuth consent | No preview for API keys | Shows scopes | Add preview for tokens (differentiator) |
| **Expiry Warnings** | 7-day email notification (2026) | No expiry (permanent tokens) | 7-day notifications | 30-day + 7-day notifications (matches industry) |
| **Method Switching** | Manual: revoke + reconnect | Manual: delete + reconnect | Manual: disconnect + reconnect | Seamless: maintain integration settings (differentiator) |

**Key insight**: Most competitors treat OAuth and tokens as completely separate integration types. Showing both in the same modal with the ability to switch seamlessly is a differentiator.

## User Experience Flow Patterns

### Pattern 1: First-Time Connection (OAuth Blocked)

**User Scenario**: Enterprise security policy blocks OAuth
**Expected Flow**:
1. User clicks "Connect with Jira" button
2. Modal opens showing two options: "OAuth" (recommended) and "API Token"
3. User sees OAuth is blocked (or tries and fails)
4. User switches to "API Token" tab
5. Sees clear instructions: "Generate token at [link to Jira docs]"
6. Pastes token, system validates in real-time
7. Preview shows: "This token grants access to: [X projects, Y users]"
8. User confirms, integration connects
9. Visual badge shows "Connected - API Token"

### Pattern 2: Switching from OAuth to Token

**User Scenario**: OAuth token keeps expiring, user wants permanent token
**Expected Flow**:
1. User sees "Connected - OAuth" on Jira card
2. Clicks "Disconnect" button
3. Confirmation dialog: "Disconnect Jira integration? Your historical data will be preserved."
4. User confirms disconnect
5. Card returns to connection state
6. User clicks "Connect with Jira" again
7. This time chooses "API Token" option
8. Completes token flow
9. Historical data and settings restored, now using token auth

### Pattern 3: Token About to Expire (if applicable)

**User Scenario**: Platform-specific token has expiry date
**Expected Flow**:
1. 30 days before expiry: Email notification + banner in app
2. 7 days before expiry: Second email + prominent warning on integration card
3. User clicks "Update Token"
4. Opens modal with token input pre-focused
5. User pastes new token
6. System validates and seamlessly updates
7. Warning clears, confirmation message shown

## Implementation Notes

### Reusable Patterns Already in Codebase

1. **Token validation flow** - `integration-handlers.ts` lines 7-105
   - Real-time validation with preview data
   - Duplicate token detection
   - Clear error messaging with user_message/user_guidance

2. **OAuth connection flow** - `jira-integration-card.tsx`
   - Modal with connection state
   - Visual status badges
   - Permission display

3. **Connection status display** - `jira-integration-card.tsx` lines 126-280
   - Badge showing OAuth
   - Token type indicator
   - Expiry date with auto-refresh indicator

**Implementation strategy**: Extend Jira/Linear integration cards to offer both OAuth and Token options using existing patterns.

### Technical Considerations

- **Token storage**: Already using server-side encrypted storage (API_BASE endpoints)
- **Validation endpoints**: Need `/jira/token/test` and `/linear/token/test` (mirror Rootly/PagerDuty pattern)
- **Token format**: Jira uses base64-encoded `email:token`, Linear uses Bearer tokens
- **Permission scopes**: Jira requires `read:jira-work`, `read:jira-user`. Linear requires `read` scope minimum
- **Team-level access**: Both platforms support organization/workspace-level tokens

## Sources

### OAuth vs Token Authentication
- [Token-Based Authentication](https://heimdalsecurity.com/blog/what-is-token-based-authentication/)
- [OAuth Token Best Practices](https://supertokens.com/blog/oauth-token)
- [Auth0 Token Best Practices](https://auth0.com/docs/secure/tokens/token-best-practices)
- [OAuth 2.0 for APIs: Flows, Tokens, and Pitfalls](https://treblle.com/blog/oauth-2.0-for-apis)
- [Why Migrate from API Keys to OAuth 2.0](https://auth0.com/blog/why-migrate-from-api-keys-to-oauth2-access-tokens/)
- [Session-Based vs Token-Based Authentication](https://securityboulevard.com/2026/01/session-based-authentication-vs-token-based-authentication-key-differences-explained/)

### User Experience Best Practices
- [Form UI/UX Design Best Practices 2026](https://www.designstudiouiux.com/blog/form-ux-design-best-practices/)
- [Input Feedback Design Pattern](https://ui-patterns.com/patterns/InputFeedback)
- [Authentication Flow Explained](https://securityboulevard.com/2026/01/authentication-flow-explained-step-by-step-login-token-exchange-process/)

### Platform-Specific Authentication
- [Jira OAuth 2.0 (3LO) Apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Linear vs Jira vs Asana APIs in 2026](https://bytepulse.io/linear-vs-jira-vs-asana-apis-in-2026/)
- [Jira API Token Best Practices](https://community.atlassian.com/forums/Jira-questions/User-API-Token-Best-Practices/qaq-p/3095043)
- [Jira Basic Auth for REST APIs](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/)

### Token Security and Management
- [API Key Security Best Practices](https://www.legitsecurity.com/aspm-knowledge-base/api-key-security-best-practices)
- [Google Cloud API Keys Best Practices](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices)
- [API Key Management Best Practices 2026](https://42crunch.com/token-management-best-practices/)
- [API Security Best Practices 2026](https://acmeminds.com/building-secure-apis-in-2026-best-practices-for-authentication-and-authorization/)

### Token Lifecycle and Rotation
- [OAuth 2 Refresh Tokens Guide](https://frontegg.com/blog/oauth-2-refresh-tokens)
- [Refresh Token Rotation Best Practices](https://www.serverion.com/uncategorized/refresh-token-rotation-best-practices-for-developers/)
- [RFC 9700 - OAuth 2.0 Security Best Practices](https://datatracker.ietf.org/doc/rfc9700/)
- [Token Lifecycle Management](https://developer.okta.com/docs/concepts/token-lifecycles/)

### Expiry and Notification Patterns
- [Intuit Refresh Token Policy Changes](https://blogs.intuit.com/2025/11/12/important-changes-to-refresh-token-policy/)
- [Azure Databricks Token Monitoring](https://learn.microsoft.com/en-us/azure/databricks/admin/access-control/tokens)
- [UiPath Integration Connections Troubleshooting](https://docs.uipath.com/integration-service/automation-cloud/latest/user-guide/connections-troubleshooting)

### Industry Trends 2026
- [Microsoft Modern Authentication Enforcement 2026](https://www.getmailbird.com/microsoft-modern-authentication-enforcement-email-guide/)
- [OAuth 2.1 Features 2026](https://rgutierrez2004.medium.com/oauth-2-1-features-you-cant-ignore-in-2026-a15f852cb723)
- [OAuth Scopes Best Practices](https://curity.io/resources/learn/scope-best-practices/)

---
*Feature research for: Token-Based Authentication Integration*
*Researched: 2026-01-30*
*Confidence: HIGH - Research based on Context7, official platform documentation, and current industry standards*
