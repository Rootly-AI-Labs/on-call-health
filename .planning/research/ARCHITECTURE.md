# Architecture Research: Dual-Auth Integration (OAuth + Token)

**Domain:** Integration authentication systems
**Researched:** 2026-01-30
**Confidence:** HIGH

## Standard Architecture

### System Overview

Dual-auth systems support both OAuth 2.0 flows (for delegated access) and direct API token flows (for manual/service access) within the same integration architecture. The pattern separates authentication method from authorization logic.

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend Layer                           │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   OAuth UI  │  │  Token UI   │  │  Status UI  │          │
│  │  (Redirect) │  │ (Form/Copy) │  │ (Validation)│          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
├─────────┴────────────────┴────────────────┴──────────────────┤
│                      API Gateway                             │
│                  (Route Selection)                           │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐          ┌──────────────────┐          │
│  │  OAuth Endpoints │          │ Manual Endpoints │          │
│  ├──────────────────┤          ├──────────────────┤          │
│  │ /connect         │          │ /manual/setup    │          │
│  │ /callback        │          │ /manual/validate │          │
│  │ /disconnect      │          │ /manual/test     │          │
│  └────────┬─────────┘          └────────┬─────────┘          │
│           │                             │                    │
│           └──────────┬──────────────────┘                    │
│                      ▼                                       │
│         ┌───────────────────────────┐                        │
│         │  Integration Validator    │                        │
│         │  (Unified Interface)      │                        │
│         └─────────┬─────────────────┘                        │
│                   │                                          │
├───────────────────┴──────────────────────────────────────────┤
│                   Service Layer                              │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │ OAuth Manager   │  │ Token Manager   │                   │
│  │ - Exchange code │  │ - Store token   │                   │
│  │ - Refresh token │  │ - Validate      │                   │
│  │ - Handle expiry │  │ - Encrypt/Drypt │                   │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           └──────────┬─────────┘                             │
│                      ▼                                       │
│         ┌───────────────────────────┐                        │
│         │  Token Abstraction Layer  │                        │
│         │  (get_valid_token())      │                        │
│         └─────────┬─────────────────┘                        │
│                   │                                          │
├───────────────────┴──────────────────────────────────────────┤
│                   Data Layer                                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Integration Model                        │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ Fields:                                               │   │
│  │ - access_token (encrypted)                            │   │
│  │ - refresh_token (encrypted, nullable for manual)      │   │
│  │ - token_source: "oauth" | "manual"                    │   │
│  │ - token_expires_at (nullable for non-expiring tokens) │   │
│  │ - platform-specific fields (cloud_id, workspace_id)   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **OAuth Endpoints** | Handle OAuth flow initialization and callback processing | FastAPI routes with redirect to provider, exchange code for token |
| **Manual Endpoints** | Accept and validate direct API tokens from users | FastAPI routes accepting token in request body, immediate validation |
| **Integration Validator** | Unified token validation regardless of source | Service class with `validate_all_integrations()` method |
| **Token Abstraction Layer** | Get valid token for API calls (refresh if needed) | `get_valid_token()` method that abstracts OAuth refresh vs manual token |
| **OAuth Manager** | Provider-specific OAuth flows (Jira, Linear, etc.) | Class per provider with `exchange_code_for_token()`, `refresh_access_token()` |
| **Token Manager** | Encrypt/decrypt tokens, handle storage | Fernet encryption, database persistence |
| **Integration Model** | Unified data model with discriminator field | SQLAlchemy model with `token_source` discriminator |

## Recommended Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── jira.py              # OAuth endpoints: /connect, /callback
│   │       ├── jira_manual.py       # Manual endpoints: /manual/setup, /manual/validate
│   │       ├── linear.py            # OAuth endpoints
│   │       └── linear_manual.py     # Manual endpoints
│   ├── auth/
│   │   └── integration_oauth.py     # OAuth managers (JiraIntegrationOAuth, LinearIntegrationOAuth)
│   ├── services/
│   │   ├── integration_validator.py # Unified validation service
│   │   ├── token_refresh_coordinator.py # Handles OAuth token refresh with locking
│   │   └── token_manager.py         # NEW: Abstraction layer for get_valid_token()
│   ├── models/
│   │   ├── jira_integration.py      # Model with token_source field
│   │   └── linear_integration.py    # Model with token_source field
│   └── core/
│       ├── encryption.py            # Centralized encryption utilities
│       └── validation_cache.py      # Cache validation results
frontend/
├── components/
│   ├── integrations/
│   │   ├── JiraOAuthSetup.tsx       # OAuth flow UI
│   │   ├── JiraManualSetup.tsx      # Manual token input UI
│   │   ├── LinearOAuthSetup.tsx     # OAuth flow UI
│   │   └── LinearManualSetup.tsx    # Manual token input UI
│   └── shared/
│       └── IntegrationStatusBadge.tsx # Shows OAuth vs Manual status
```

### Structure Rationale

- **Separate route files for OAuth vs Manual**: Clear separation of concerns, easier to maintain distinct flows
- **Token abstraction layer**: `get_valid_token()` hides whether token came from OAuth (needs refresh) or manual (no refresh)
- **Discriminator field**: `token_source` on model enables conditional logic without separate tables
- **Unified validator**: Same validation logic regardless of token source, simplifies integration checks
- **Frontend UI separation**: Users see different flows based on auth method, but same status display

## Architectural Patterns

### Pattern 1: Strategy Pattern for Token Retrieval

**What:** Abstraction layer that provides valid tokens regardless of source (OAuth with refresh vs manual without refresh)

**When to use:** When the same API client needs tokens from different sources but shouldn't care about token lifecycle

**Trade-offs:**
- ✅ Clean separation: API clients don't need to know about OAuth refresh logic
- ✅ Easier to add new auth methods (e.g., service accounts, machine tokens)
- ❌ Additional abstraction layer adds complexity
- ❌ Must handle both expiring (OAuth) and non-expiring (manual API key) tokens

**Example:**
```python
class TokenManager:
    """Abstraction layer for retrieving valid tokens."""

    async def get_valid_token(self, integration: Integration) -> str:
        """Get a valid access token, refreshing OAuth tokens if needed."""
        if integration.token_source == "oauth":
            return await self._get_oauth_token(integration)
        elif integration.token_source == "manual":
            return await self._get_manual_token(integration)
        else:
            raise ValueError(f"Unknown token source: {integration.token_source}")

    async def _get_oauth_token(self, integration: Integration) -> str:
        """Get OAuth token, refreshing if expired."""
        if needs_refresh(integration.token_expires_at):
            return await self._refresh_oauth_token(integration)
        return decrypt_token(integration.access_token)

    async def _get_manual_token(self, integration: Integration) -> str:
        """Get manual API token (no refresh needed)."""
        return decrypt_token(integration.access_token)
```

### Pattern 2: Discriminator Field Pattern

**What:** Single integration table with `token_source` field to differentiate OAuth vs manual authentication

**When to use:** When integration behavior is 95% shared, only authentication method differs

**Trade-offs:**
- ✅ Single source of truth for integration data
- ✅ Easier to query "all integrations for user" regardless of auth method
- ✅ Avoids data duplication (workspace_id, user mappings, etc.)
- ❌ Some fields nullable for one method but not the other (e.g., `refresh_token`)
- ❌ Conditional logic based on `token_source` scattered throughout code

**Example:**
```python
class JiraIntegration(Base):
    __tablename__ = "jira_integrations"

    # Shared fields
    user_id = Column(Integer, ForeignKey("users.id"))
    jira_cloud_id = Column(String)
    jira_site_url = Column(String)

    # Auth fields
    access_token = Column(Text)  # Always present, encrypted
    refresh_token = Column(Text, nullable=True)  # Only for OAuth
    token_source = Column(String, default="oauth")  # "oauth" | "manual"
    token_expires_at = Column(DateTime, nullable=True)  # Only for OAuth

    @property
    def supports_refresh(self) -> bool:
        return self.token_source == "oauth" and self.refresh_token is not None
```

### Pattern 3: Unified Validation Interface

**What:** Same validation method for all integrations, regardless of auth source

**When to use:** Always - validation logic should be identical (make API call to verify token works)

**Trade-offs:**
- ✅ Consistent user experience across auth methods
- ✅ Single cache for validation results
- ✅ Simpler to add new integrations
- ❌ Must handle OAuth token refresh during validation

**Example:**
```python
class IntegrationValidator:
    async def validate_all_integrations(self, user_id: int) -> Dict[str, Dict[str, Any]]:
        """Validate all integrations regardless of auth source."""
        results = {}

        # Jira validation (OAuth or manual)
        if jira_integration := self._get_jira(user_id):
            token = await self.token_manager.get_valid_token(jira_integration)
            results["jira"] = await self._validate_jira_api(token, jira_integration.jira_cloud_id)

        return results

    async def _validate_jira_api(self, token: str, cloud_id: str) -> Dict[str, Any]:
        """Test Jira API with token (doesn't care if OAuth or manual)."""
        response = await httpx.get(
            f"https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself",
            headers={"Authorization": f"Bearer {token}"}
        )
        return {"valid": response.status_code == 200}
```

## Data Flow

### OAuth Flow (Existing)

```
User clicks "Connect Jira"
    ↓
Frontend: POST /jira/connect
    ↓
Backend: Generate OAuth URL with state
    ↓
Frontend: Redirect to Jira OAuth page
    ↓
User authorizes in Jira
    ↓
Jira: Redirect to {FRONTEND_URL}/setup/jira/callback?code=XXX&state=YYY
    ↓
Frontend: POST /jira/callback with code
    ↓
Backend: Exchange code for access_token + refresh_token
    ↓
Backend: Store in DB with token_source="oauth"
    ↓
Backend: Return success
    ↓
Frontend: Redirect to /integrations?jira_connected=1
```

### Manual Token Flow (New)

```
User clicks "Use API Token"
    ↓
Frontend: Show form with token input field
    ↓
User pastes API token from Jira settings
    ↓
User enters Jira site URL (e.g., "mycompany.atlassian.net")
    ↓
Frontend: POST /jira/manual/setup
    {
        "api_token": "user_provided_token",
        "site_url": "mycompany.atlassian.net"
    }
    ↓
Backend: Validate token immediately (call Jira API)
    ↓
Backend: If valid, get cloud_id and user info
    ↓
Backend: Store in DB with token_source="manual", refresh_token=null
    ↓
Backend: Return success
    ↓
Frontend: Show success message, redirect to /integrations
```

### Unified Validation Flow

```
User navigates to /analysis (or periodic background job)
    ↓
Backend: GET /integrations/validate (or internal service call)
    ↓
IntegrationValidator.validate_all_integrations(user_id)
    ↓
For each integration:
    ├─ Get integration from DB
    ├─ Check token_source field
    ├─ If OAuth: get_valid_token() → checks expiry → refreshes if needed
    ├─ If Manual: get_valid_token() → returns stored token
    ├─ Make API call to provider (Jira /myself, Linear viewer query, etc.)
    ├─ Return {valid: true/false, error: "..."}
    └─ Cache result for 5 minutes
    ↓
Return validation results to frontend
    ↓
Frontend: Display status badges (OAuth vs Manual, Valid vs Invalid)
```

## Scaling Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| **Token refresh concurrency** | In-process locking sufficient | Redis-based distributed locks for OAuth refresh | Dedicated token refresh service with queue |
| **Validation caching** | In-memory cache (5 min TTL) | Redis cache with 5 min TTL | Redis cache + invalidation on token update |
| **OAuth callback handling** | Single backend instance | Multiple instances with session store in Redis | Load balancer with sticky sessions or stateless approach |
| **Manual token validation** | Synchronous validation on setup | Background validation job after setup | Rate-limited validation with circuit breaker for provider APIs |

## Anti-Patterns to Avoid

### Anti-Pattern 1: Separate Tables for OAuth vs Manual

**What people do:** Create `jira_oauth_integrations` and `jira_manual_integrations` tables

**Why it's wrong:**
- Data duplication (workspace mappings, user correlations must exist in both)
- Complex queries ("get all Jira integrations for user" needs UNION)
- Hard to migrate users between auth methods
- Business logic must handle two code paths for everything

**Do this instead:** Use single table with `token_source` discriminator field

### Anti-Pattern 2: Exposing Token Source to API Clients

**What people do:** Every API client checks `if integration.token_source == "oauth"` before calling provider API

**Why it's wrong:**
- Business logic polluted with authentication concerns
- Hard to add new auth methods (every client needs updates)
- Token refresh logic scattered across codebase
- Difficult to test

**Do this instead:** Use token abstraction layer with `get_valid_token()` method that hides refresh logic

### Anti-Pattern 3: Different Validation Logic for OAuth vs Manual

**What people do:** Separate validation methods that behave differently based on token source

**Why it's wrong:**
- Inconsistent user experience (OAuth users see different errors than manual users)
- Duplicate validation logic with subtle differences
- Cache invalidation becomes complex
- Frontend must know about token source to display status correctly

**Do this instead:** Unified validation interface that makes same API call regardless of token source

### Anti-Pattern 4: No Token Expiry Handling for Manual Tokens

**What people do:** Assume manual API tokens never expire, skip validation

**Why it's wrong:**
- Many providers do expire API tokens (Jira Cloud tokens can be revoked)
- Users don't know their integration is broken until analysis fails
- No proactive notification of invalid tokens
- Poor user experience

**Do this instead:** Validate all tokens periodically (manual and OAuth), surface errors to users

### Anti-Pattern 5: Frontend Duplication for OAuth vs Manual

**What people do:** Completely separate UI components with duplicated logic

**Why it's wrong:**
- Maintenance burden (bug fixes need to be applied twice)
- Inconsistent user experience
- Hard to share common elements (status display, disconnection, etc.)

**Do this instead:** Shared status components, separate only the auth flow UI (redirect vs form)

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Jira Cloud OAuth** | OAuth 2.0 (3LO) with refresh tokens | 1-hour token expiry, requires refresh_token |
| **Jira Cloud API Token** | Personal Access Token (PAT) in Authorization header | Does not expire automatically, user-managed |
| **Linear OAuth** | OAuth 2.0 with PKCE | 24-hour token expiry, optional refresh |
| **Linear API Key** | API key in Authorization header | No expiry, workspace-scoped |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Frontend ↔ OAuth Endpoints** | REST API (POST /connect, POST /callback) | OAuth endpoints return redirect URLs, frontend handles navigation |
| **Frontend ↔ Manual Endpoints** | REST API (POST /manual/setup) | Synchronous validation, return success/error immediately |
| **Endpoints ↔ Integration Validator** | Direct service call | Validator used for pre-flight checks before analysis |
| **Integration Validator ↔ Token Manager** | Direct method call | Abstraction layer for token retrieval |
| **Token Manager ↔ OAuth Manager** | Direct method call | OAuth-specific refresh logic |
| **All layers ↔ Integration Model** | SQLAlchemy ORM | Single model accessed by all layers |

## Build Order Dependencies

Recommended implementation order to minimize disruption:

### Phase 1: Data Model Extension
**Goal:** Add discriminator field to existing models
**Dependencies:** None (extends existing schema)
**Build:**
1. Add `token_source` column to `jira_integration` table (default "oauth")
2. Add `token_source` column to `linear_integration` table (default "oauth")
3. Migration to set all existing records to "oauth"
4. Add model properties: `is_oauth`, `is_manual`, `supports_refresh`

### Phase 2: Token Abstraction Layer
**Goal:** Create unified token retrieval interface
**Dependencies:** Phase 1 (needs `token_source` field)
**Build:**
1. Create `TokenManager` service class
2. Implement `get_valid_token()` method with OAuth refresh logic
3. Update `IntegrationValidator` to use `TokenManager`
4. Test with existing OAuth integrations (should work unchanged)

### Phase 3: Manual Token Storage
**Goal:** Accept and store manual API tokens
**Dependencies:** Phase 1, Phase 2
**Build:**
1. Create `/jira/manual/setup` endpoint
2. Validate token by calling Jira API
3. Store with `token_source="manual"`, `refresh_token=null`
4. Create `/linear/manual/setup` endpoint
5. Validate token by calling Linear API
6. Store with `token_source="manual"`

### Phase 4: Frontend UI
**Goal:** User-facing manual token input
**Dependencies:** Phase 3 (needs backend endpoints)
**Build:**
1. Create manual token input forms
2. Add UI switcher (OAuth vs Manual)
3. Update status badges to show auth method
4. Add help text for obtaining manual tokens

### Phase 5: Unified Validation Display
**Goal:** Show validation status regardless of auth method
**Dependencies:** Phase 2, Phase 3
**Build:**
1. Update validation response to include `token_source`
2. Frontend displays OAuth vs Manual in status
3. Different error messages for OAuth (reconnect) vs Manual (re-enter token)

## Key Decisions for Implementation

### Decision 1: Single Table vs Separate Tables
**Recommendation:** Single table with `token_source` discriminator
**Rationale:**
- Integration data (workspace, user mappings) is identical regardless of auth
- Simpler queries for "all integrations"
- Easier to migrate users between auth methods if needed
- SQLAlchemy handles discriminator patterns well

### Decision 2: Token Refresh During Validation
**Recommendation:** Always attempt refresh for OAuth tokens during validation
**Rationale:**
- Validation is the right time to discover expired tokens
- User sees accurate status (not "valid" when token is actually expired)
- Prevents analysis failures due to expired tokens
- Uses existing token refresh infrastructure

### Decision 3: Manual Token Validation Frequency
**Recommendation:** Validate manual tokens same as OAuth (cached 5 min)
**Rationale:**
- Manual tokens can be revoked by user in provider settings
- Consistent UX (OAuth and manual users see same validation behavior)
- Prevents surprises during analysis ("why did my manual token stop working?")

### Decision 4: Frontend UI Strategy
**Recommendation:** Separate setup components, shared status components
**Rationale:**
- Setup flows are fundamentally different (redirect vs form)
- Status display is identical (valid/invalid, last validated)
- Reduces code duplication
- Clear user experience (choose auth method, then distinct flow)

## Sources

### OAuth & API Token Architecture (2026)
- [Curity: Token Patterns](https://curity.io/resources/learn/token-patterns/)
- [Microservices.io: Authentication in Microservices - Part 2](https://microservices.io/post/architecture/2025/05/28/microservices-authn-authz-part-2-authentication.html)
- [ACMEMinds: Building Secure APIs in 2026](https://acmeminds.com/building-secure-apis-in-2026-best-practices-for-authentication-and-authorization/)

### Dual Authentication Support
- [Auth0: Why Migrate from API Keys to OAuth2](https://auth0.com/blog/why-migrate-from-api-keys-to-oauth2-access-tokens/)
- [Nordic APIs: HTTP Auth, API Keys, and OAuth](https://nordicapis.com/the-difference-between-http-auth-api-keys-and-oauth/)
- [Axway: API Keys vs OAuth Best Practices](https://blog.axway.com/learning-center/digital-security/keys-oauth/api-keys-oauth)

### FastAPI Multiple Auth Strategies
- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [GitHub Issue #1550: Multiple Authentication Types](https://github.com/fastapi/fastapi/issues/1550)
- [Better Stack: Authentication with FastAPI](https://betterstack.com/community/guides/scaling-python/authentication-fastapi/)
- [Practical FastAPI Security Guide (2025)](https://blog.greeden.me/en/2025/12/30/practical-fastapi-security-guide-designing-modern-apis-protected-by-jwt-auth-oauth2-scopes-and-api-keys/)

### Unified API Patterns
- [Merge.dev: What is a Unified API](https://www.merge.dev/blog/what-is-a-unified-api)
- [Microservices.io: API Gateway Pattern](https://microservices.io/patterns/security/access-token.html)

### API Security Best Practices (2026)
- [Xano: Modern API Design Best Practices](https://www.xano.com/blog/modern-api-design-best-practices/)
- [Informatica: Enterprise API Security Architecture](https://www.informatica.com/resources/articles/enterprise-api-security-architecture.html)
- [Curity: API Security Trends 2026](https://curity.io/blog/api-security-trends-2026/)
- [Devcom: API Security Best Practices 2026](https://devcom.com/tech-blog/api-security-best-practices-protect-your-data/)

---
*Architecture research for: Token-based authentication integration alongside OAuth*
*Researched: 2026-01-30*
*Confidence: HIGH - based on current architecture inspection + verified industry patterns*
