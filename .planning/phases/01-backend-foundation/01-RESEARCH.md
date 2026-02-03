# Phase 1: Backend Foundation - Research

**Researched:** 2026-02-01
**Domain:** Token management abstraction layer with encryption parity
**Confidence:** HIGH

## Summary

Research into the On-Call-Health codebase reveals that **much of Phase 1 infrastructure already exists**. The `token_source` discriminator field is present on both `JiraIntegration` and `LinearIntegration` models (migration 011 and 023), along with the `is_oauth`, `is_manual`, and `supports_refresh` computed properties. Encryption utilities (`encrypt_token()`, `decrypt_token()`) are implemented in `integration_validator.py` using Fernet with ENCRYPTION_KEY.

The primary work for this phase is:
1. **Create TokenManager service** - A new service at `app/services/token_manager.py` that provides `get_valid_token()` abstraction
2. **Unify existing token retrieval logic** - Extract `_get_valid_jira_token()` and `_get_valid_linear_token()` patterns from `IntegrationValidator`
3. **Add security tests** - Verify encryption parity between OAuth and manual tokens

**Primary recommendation:** Extract existing token retrieval logic into a dedicated TokenManager service, leveraging the established encryption utilities and token refresh patterns.

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| cryptography (Fernet) | existing | Token encryption/decryption | Project already uses, standard symmetric encryption |
| SQLAlchemy | existing | ORM for integration models | Project standard, models already defined |
| redis | existing | Distributed locking, caching | Project uses for token refresh coordination |
| httpx | existing | Async HTTP client for API calls | Project standard for external API calls |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | existing | Environment variable loading | ENCRYPTION_KEY retrieval |
| unittest.mock | stdlib | Testing mocks | Unit tests for TokenManager |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Fernet encryption | AES-GCM directly | Fernet is simpler, already in use, no migration needed |
| Custom encryption utilities | Third-party secret manager | Adds dependency, current approach works, ENCRYPTION_KEY already configured |

**Installation:**
No new packages required - all dependencies already in `requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/services/
├── integration_validator.py  # Existing - validation logic
├── token_refresh_coordinator.py  # Existing - distributed locking
└── token_manager.py          # NEW - get_valid_token() abstraction
```

### Pattern 1: Token Retrieval Abstraction (Strategy Pattern)
**What:** Single method `get_valid_token(integration)` that hides OAuth refresh vs manual token differences
**When to use:** Any code that needs a token to call external APIs (Jira, Linear, etc.)
**Example:**
```python
# Source: Extracted from app/services/integration_validator.py lines 452-470, 229-276
class TokenManager:
    """Abstraction layer for retrieving valid tokens."""

    def __init__(self, db: Session):
        self.db = db

    async def get_valid_token(
        self,
        integration: Union[JiraIntegration, LinearIntegration]
    ) -> str:
        """Get a valid access token, refreshing OAuth tokens if needed.

        For OAuth tokens: Checks expiry, refreshes if needed, returns decrypted token
        For manual tokens: Returns decrypted token directly (no refresh possible)

        Raises:
            ValueError: If token is invalid or refresh fails
        """
        if integration.is_oauth:
            return await self._get_oauth_token(integration)
        elif integration.is_manual:
            return await self._get_manual_token(integration)
        else:
            raise ValueError(f"Unknown token source: {integration.token_source}")

    async def _get_oauth_token(self, integration) -> str:
        """Get OAuth token, refreshing if expired."""
        # Delegate to existing _get_valid_jira_token / _get_valid_linear_token logic
        # which handles distributed locking and refresh

    async def _get_manual_token(self, integration) -> str:
        """Get manual API token (no refresh needed)."""
        return decrypt_token(integration.access_token)
```

### Pattern 2: Existing Token Source Discriminator
**What:** `token_source` field on integration models with computed properties
**Already Implemented:** Models have `is_oauth`, `is_manual`, `supports_refresh` properties
**Example:**
```python
# Source: backend/app/models/jira_integration.py lines 30, 54-66
class JiraIntegration(Base):
    token_source = Column(String(20), default="oauth")  # 'oauth' or 'manual'

    @property
    def is_oauth(self) -> bool:
        return self.token_source == "oauth"

    @property
    def is_manual(self) -> bool:
        return self.token_source == "manual"

    @property
    def supports_refresh(self) -> bool:
        return self.is_oauth and self.has_refresh_token
```

### Pattern 3: Encryption Utilities
**What:** Fernet encryption for all tokens using ENCRYPTION_KEY
**Already Implemented:** `encrypt_token()` and `decrypt_token()` in integration_validator.py
**Example:**
```python
# Source: backend/app/services/integration_validator.py lines 29-56
def get_encryption_key() -> bytes:
    """Get the encryption key from settings."""
    from base64 import urlsafe_b64encode
    key = settings.ENCRYPTION_KEY.encode()
    key = urlsafe_b64encode(key[:32].ljust(32, b'\0'))
    return key

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()

def encrypt_token(token: str) -> str:
    """Encrypt a token for storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token.encode()).decode()
```

### Anti-Patterns to Avoid
- **Don't duplicate encryption logic:** Use existing `encrypt_token()`/`decrypt_token()` from integration_validator.py
- **Don't skip distributed locking for OAuth refresh:** Use existing `refresh_token_with_lock()` from token_refresh_coordinator.py
- **Don't expose token_source checks to API clients:** All token retrieval should go through TokenManager

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token encryption | Custom encryption | `encrypt_token()`/`decrypt_token()` in integration_validator.py | Already handles key derivation, Fernet setup |
| OAuth token refresh | Simple refresh call | `refresh_token_with_lock()` in token_refresh_coordinator.py | Handles distributed locking, race conditions |
| Validation caching | In-memory cache | `validation_cache.py` | Handles Redis fallback, TTL, cache eviction |
| Expiry checking | Manual datetime comparison | `needs_refresh()` in integration_validator.py | Handles timezone, configurable skew |

**Key insight:** The codebase already has battle-tested implementations for token encryption, refresh coordination, and caching. TokenManager should compose these existing utilities, not reimplement them.

## Common Pitfalls

### Pitfall 1: Duplicating Token Refresh Logic
**What goes wrong:** Creating new OAuth refresh logic in TokenManager instead of reusing existing IntegrationValidator methods
**Why it happens:** Existing methods are private (`_get_valid_jira_token`), so developers create new ones
**How to avoid:** Extract existing private methods or make TokenManager a collaborator with IntegrationValidator
**Warning signs:** New OAuth API calls in TokenManager, new distributed locking code

### Pitfall 2: Forgetting Manual Token Encryption
**What goes wrong:** Storing manual tokens in plaintext because "they're user-provided"
**Why it happens:** OAuth tokens arrive encrypted from provider, mental model doesn't carry to manual tokens
**How to avoid:** Always call `encrypt_token()` before storage, always call `decrypt_token()` before use
**Warning signs:** Direct access to `integration.access_token` without decrypt call for manual tokens

### Pitfall 3: Not Handling Missing Tokens
**What goes wrong:** NoneType errors when accessing `integration.access_token`
**Why it happens:** Integration exists but token is None (disconnected, initial setup failed)
**How to avoid:** Check `integration.has_token` before attempting decryption
**Warning signs:** Unhandled exceptions in production when accessing tokens

### Pitfall 4: Assuming Manual Tokens Never Expire
**What goes wrong:** No validation of manual tokens, leading to silent failures during analysis
**Why it happens:** API tokens don't technically expire, so validation is skipped
**How to avoid:** Manual tokens should still be validated periodically (15min cache pattern exists)
**Warning signs:** Manual token integrations show "valid" status but fail during actual API calls

### Pitfall 5: Inconsistent Error Messages
**What goes wrong:** OAuth errors say "reconnect", manual errors say "token invalid" - confusing UX
**Why it happens:** Different code paths for OAuth vs manual
**How to avoid:** TokenManager should return consistent error types regardless of token source
**Warning signs:** Different error handling in IntegrationValidator vs new TokenManager code

## Code Examples

Verified patterns from the codebase:

### Existing OAuth Token Retrieval (Jira)
```python
# Source: backend/app/services/integration_validator.py lines 452-499
async def _get_valid_jira_token(self, integration: JiraIntegration) -> str:
    """Get a valid Jira access token, refreshing if necessary."""
    if not integration.access_token:
        raise ValueError("No access token available for Jira integration")

    self.db.refresh(integration)

    token_needs_refresh = needs_refresh(integration.token_expires_at)
    has_refresh_token = bool(integration.refresh_token)

    if not token_needs_refresh:
        return decrypt_token(integration.access_token)

    if not has_refresh_token:
        raise ValueError("Authentication error. Please reconnect Jira.")

    # Use coordinator with distributed locking
    token = await refresh_token_with_lock(
        provider="jira",
        integration_id=integration.id,
        user_id=integration.user_id,
        refresh_func=lambda: self._perform_jira_token_refresh(integration),
        fallback_func=lambda: self._perform_jira_token_refresh_with_db_lock(integration)
    )
    return token
```

### Existing Token Encryption
```python
# Source: backend/app/services/integration_validator.py lines 47-56
def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a token from storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.decrypt(encrypted_token.encode()).decode()

def encrypt_token(token: str) -> str:
    """Encrypt a token for storage."""
    fernet = Fernet(get_encryption_key())
    return fernet.encrypt(token.encode()).decode()
```

### Existing Test Pattern for Token Operations
```python
# Source: backend/tests/test_integration_validator.py lines 166-184
@patch('app.services.integration_validator.decrypt_token')
def test_validate_linear_success(self, mock_decrypt):
    """Test successful Linear validation."""
    mock_integration = Mock(spec=LinearIntegration)
    mock_integration.access_token = "encrypted_token"
    mock_integration.token_expires_at = datetime.now(dt_timezone.utc) + timedelta(hours=12)
    mock_integration.refresh_token = None
    self.mock_db.query().filter().first.return_value = mock_integration
    mock_decrypt.return_value = "valid_token"

    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"viewer": {"id": "123"}}}
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)

        result = self._run_async(self.validator._validate_linear(user_id=1))

    self.assertTrue(result["valid"])
```

### Model Property Pattern
```python
# Source: backend/app/models/linear_integration.py lines 60-73
@property
def is_oauth(self) -> bool:
    """Check if this integration uses OAuth tokens."""
    return self.token_source == "oauth"

@property
def is_manual(self) -> bool:
    """Check if this integration uses manual API key."""
    return self.token_source == "manual"

@property
def supports_refresh(self) -> bool:
    """Check if this integration supports token refresh."""
    return self.is_oauth and self.has_refresh_token
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Scattered token retrieval in validators | Centralized TokenManager (Phase 1 goal) | This phase | Cleaner API for token access |
| OAuth-only token support | OAuth + Manual token support | Already in models | Broader auth options |

**Already implemented:**
- `token_source` discriminator field (migrations 011, 023)
- `is_oauth`, `is_manual`, `supports_refresh` properties
- Fernet encryption with ENCRYPTION_KEY
- Distributed locking for token refresh
- Validation caching (5 min TTL)

**Deprecated/outdated:**
- None - existing patterns are current

## Implementation Checklist (Verified Against Context)

Based on CONTEXT.md decisions, the following must be implemented:

### 1. TokenManager Service (NEW)
- [ ] Create `backend/app/services/token_manager.py`
- [ ] Implement `get_valid_token(integration)` method
- [ ] Delegate OAuth refresh to existing `_get_valid_*_token()` methods or extracted logic
- [ ] Handle manual tokens with simple `decrypt_token()` call
- [ ] Include 15min validation cache pattern (reuse existing cache utilities)

### 2. Security Tests (NEW)
- [ ] Test that manual tokens are encrypted with same key as OAuth tokens
- [ ] Test encryption/decryption round-trip for both token types
- [ ] Test no plaintext tokens in database (query and verify)
- [ ] Test TokenManager never returns plaintext in error messages
- [ ] Extend existing tests in `test_integration_validator.py`

### 3. Database Schema (ALREADY EXISTS)
- [x] `token_source` column on jira_integrations (migration 011)
- [x] `token_source` column on linear_integrations (migration 023)
- [x] Default value 'oauth' for existing records
- [x] NOT NULL constraint after backfilling

### 4. Model Properties (ALREADY EXISTS)
- [x] `is_oauth` property on JiraIntegration
- [x] `is_manual` property on JiraIntegration
- [x] `supports_refresh` property on JiraIntegration
- [x] Same properties on LinearIntegration

## Open Questions

Things that couldn't be fully resolved:

1. **TokenManager extraction approach**
   - What we know: Existing `_get_valid_*_token()` methods in IntegrationValidator work correctly
   - What's unclear: Should TokenManager call IntegrationValidator methods or duplicate the logic?
   - Recommendation: Extract common logic to TokenManager, have IntegrationValidator call TokenManager (dependency inversion)

2. **Manual token virtual expiration**
   - What we know: CONTEXT.md mentions "virtual expiration" for manual tokens with 15min cache
   - What's unclear: Is this separate from validation caching or the same concept?
   - Recommendation: Use existing validation cache - "virtual expiration" means "validate on first use after cache expires"

## Sources

### Primary (HIGH confidence)
- `backend/app/services/integration_validator.py` - Existing encryption utilities, token refresh logic
- `backend/app/models/jira_integration.py` - Token source field, computed properties
- `backend/app/models/linear_integration.py` - Token source field, computed properties
- `backend/migrations/migration_runner.py` - Migrations 011, 023 confirm schema exists
- `backend/tests/test_integration_validator.py` - Existing test patterns

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` - Architectural patterns for dual-auth
- `.planning/phases/01-backend-foundation/01-CONTEXT.md` - User decisions for this phase

### Tertiary (LOW confidence)
- None - all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in use, verified in requirements.txt and imports
- Architecture: HIGH - Patterns extracted from existing codebase, not hypothetical
- Pitfalls: HIGH - Based on actual codebase patterns and common issues observed

**Research date:** 2026-02-01
**Valid until:** 2026-03-01 (30 days - stable patterns, no external dependencies)

---

## Key Insight for Planner

**Phase 1 is primarily extraction and organization, not greenfield development.**

The encryption utilities, model properties, and token refresh logic already exist and work. The TokenManager service is a refactoring to provide a cleaner abstraction layer, not a new feature implementation. Security tests are the main new work.

**Recommended task breakdown:**
1. Create TokenManager service file
2. Extract/delegate to existing token retrieval logic
3. Write security tests for encryption parity
4. Write integration tests for TokenManager
5. Update IntegrationValidator to use TokenManager (optional, can be deferred)
