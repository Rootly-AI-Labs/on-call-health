# Requirements: On-Call Health Token Authentication

**Defined:** 2026-01-30
**Core Value:** Catch exhaustion before it burns out team members by analyzing cross-platform activity patterns, on-call load, and workload distribution.

## v1 Requirements

Requirements for token-based authentication feature. Each maps to roadmap phases.

### Authentication Setup

- [ ] **AUTH-01**: User can choose between OAuth and API Token when connecting Jira integration
- [ ] **AUTH-02**: User can choose between OAuth and API Token when connecting Linear integration
- [ ] **AUTH-03**: Token validation executes during setup to verify token works
- [ ] **AUTH-04**: Clear error messages display when token validation fails
- [ ] **AUTH-05**: Visual status indicators show connection state (connected, validating, error)

### Token Management

- [ ] **TOKEN-01**: API tokens stored with same encryption as OAuth tokens (Fernet with ENCRYPTION_KEY)
- [ ] **TOKEN-02**: Token validity checked using existing validation mechanism (IntegrationValidator service)
- [ ] **TOKEN-03**: Connection testing executes before saving token to database

### User Experience

- [ ] **UX-01**: Integration setup modal shows both OAuth and Token options when user clicks integration icon
- [ ] **UX-02**: Help text provides guidance for obtaining tokens from Jira (Personal Access Token)
- [ ] **UX-03**: Help text provides guidance for obtaining tokens from Linear (Personal API Key)
- [ ] **UX-04**: Integration page displays which auth method is used (OAuth vs Token) for each connected integration
- [ ] **UX-05**: Platform-specific error messages display for Jira token failures (format, permissions)
- [ ] **UX-06**: Platform-specific error messages display for Linear token failures (format, permissions)

### Method Switching

- [ ] **SWITCH-01**: User can disconnect existing OAuth integration and reconnect with API token without data loss
- [ ] **SWITCH-02**: User can disconnect existing API token integration and reconnect with OAuth without data loss

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Authentication Setup

- **AUTH-06**: Security warning displays about token permissions before user enters token
- **AUTH-07**: Permission scope preview displays before connection (show what data token can access)
- **AUTH-08**: Duplicate token detection warns user if same token is used in multiple integrations

### User Experience

- **UX-07**: Decision guidance helps user choose between OAuth and token based on their situation

### Token Management

- **TOKEN-04**: Proactive expiry notifications remind users to rotate tokens (even though tokens don't expire)
- **TOKEN-05**: Token health dashboard shows status of all API token integrations across organization

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Token-based auth for GitHub, Slack, Rootly, PagerDuty | Only Jira and Linear for this feature—other integrations work fine with OAuth |
| Automated token permission verification | No reliable API to test team-level access programmatically—trust user knows their token setup |
| Automatic token rotation | API tokens don't expire like OAuth tokens; rotation is manual user action |
| Migration wizard from OAuth to token | Users can manually disconnect/reconnect if switching—automated migration adds complexity without clear value |
| Token sharing across organizations | Security risk—each integration should use unique token |
| Client-side token storage | Security risk—all tokens must be server-side encrypted |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 3 | Pending |
| AUTH-02 | Phase 4 | Complete |
| AUTH-03 | Phase 2 | Pending |
| AUTH-04 | Phase 2 | Pending |
| AUTH-05 | Phase 2 | Pending |
| TOKEN-01 | Phase 1 | Complete |
| TOKEN-02 | Phase 1 | Complete |
| TOKEN-03 | Phase 1 | Complete |
| UX-01 | Phase 3, Phase 4 | Complete |
| UX-02 | Phase 3 | Pending |
| UX-03 | Phase 4 | Complete |
| UX-04 | Phase 5 | Complete |
| UX-05 | Phase 3 | Pending |
| UX-06 | Phase 4 | Complete |
| SWITCH-01 | Phase 5 | Complete |
| SWITCH-02 | Phase 5 | Complete |

**Coverage:**
- v1 requirements: 16 total
- Mapped to phases: 16 (100% coverage)
- Unmapped: 0

**Note:** UX-01 appears in both Phase 3 (Jira) and Phase 4 (Linear) as it applies to both platforms. Each phase implements its platform-specific version.

---
*Requirements defined: 2026-01-30*
*Last updated: 2026-01-31 after roadmap creation*
