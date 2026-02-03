# Phase 1: Backend Foundation - Implementation Context

**Phase Goal:** Establish secure token storage architecture with encryption parity between OAuth and API tokens

**Discussed:** 2026-01-31

## Phase Boundary

### In Scope
- Token storage architecture with encryption parity
- Database schema modifications (discriminator field, properties)
- TokenManager service abstraction layer
- Integration model enhancements (is_oauth, is_manual, supports_refresh)
- Security tests verifying encryption consistency
- Foundation for both Jira and Linear token support

### Out of Scope
- Token validation logic (Phase 2: Validation Infrastructure)
- UI/UX for token setup (Phase 3: Jira, Phase 4: Linear)
- Platform-specific token implementations (Phase 3: Jira, Phase 4: Linear)
- Error messages and visual indicators (Phase 2)
- Method switching between OAuth and tokens (Phase 5)

## Implementation Decisions

### 1. Database Schema Approach

**Token Source Discriminator:**
- Add `token_source` field to integration models
- Values: 'oauth' | 'manual'
- Type: String/Enum stored in database
- **User decision:** No indexes on token_source initially

**Integration Model Properties:**
- `is_oauth`: Returns True if token_source == 'oauth'
- `is_manual`: Returns True if token_source == 'manual'
- `supports_refresh`: Returns True if token_source == 'oauth'
- Properties are computed from token_source (not stored fields)

**Encryption:**
- Use same Fernet encryption as OAuth tokens
- Encryption key: ENCRYPTION_KEY from environment
- Apply to all tokens regardless of source
- No plaintext tokens in database

### 2. Token Abstraction Layer

**TokenManager Service:**
- **User decision:** Create new service in `app/services/token_manager.py`
- Core method: `get_valid_token(integration)` returns decrypted, valid token
- Handles OAuth refresh logic internally (transparent to callers)
- Handles manual token virtual expiration checks
- Returns ready-to-use token string or raises appropriate error

**Service Responsibilities:**
- Token decryption (both OAuth and manual)
- OAuth token refresh when expired
- Manual token virtual expiration validation
- Error handling (network failures, invalid tokens, expired tokens)
- Cache management (reuse existing 15min cache pattern)

**Platform Handling:**
- Unified TokenManager works for both Jira and Linear
- Platform-specific logic (if needed) handled via integration type
- No separate JiraTokenManager or LinearTokenManager initially

### 3. Token Expiration Handling

**OAuth Tokens:**
- Existing behavior: Check expiry, refresh if needed using refresh_token
- Transparent refresh via TokenManager
- Update access_token and expires_at in database after refresh

**Manual Tokens:**
- No actual expiration (API tokens don't expire)
- Virtual expiration concept: Assume token is valid until validation fails
- **User decision:** Validation frequency same as OAuth (15min cache)
- No refresh mechanism (manual tokens can't be refreshed)

**Validation Cache:**
- Reuse existing 15min validation cache pattern
- Cache key includes integration ID and token source
- Prevents excessive API calls during validation
- Cache invalidated on validation failure

### 4. Testing Strategy

**Test Scope:**
- **User decision:** Integration tests with real database for both token types
- Test TokenManager with actual OAuth and manual token records
- Verify end-to-end token retrieval and validation flow

**Discriminator Field Testing:**
- **User decision:** Database-level tests verifying queries filter correctly
- Test that queries using token_source return correct token types
- Test that is_oauth, is_manual, supports_refresh properties return correct values
- Verify ORM behavior with discriminator field

**Encryption Parity:**
- Security tests verifying both OAuth and manual tokens use same encryption
- Test that no plaintext tokens exist in database
- Test encryption/decryption round-trip for both token types
- Verify encryption key usage is consistent

**Security Tests:**
- Extend existing OAuth security tests to cover manual tokens
- Test log sanitization (no tokens in logs)
- Test encryption at rest (database snapshots show encrypted tokens)
- Test that TokenManager never returns plaintext in error messages

## Specific Ideas

### Database Migration
- Add `token_source` column to jira_integrations and linear_integrations tables
- Default existing records to 'oauth' (all current integrations use OAuth)
- Set NOT NULL constraint after backfilling
- No index on token_source initially (low cardinality, not heavily queried)

### TokenManager Implementation Pattern
```python
class TokenManager:
    def get_valid_token(self, integration: Integration) -> str:
        """Returns decrypted, validated token for integration."""
        if integration.is_oauth:
            return self._get_oauth_token(integration)
        else:
            return self._get_manual_token(integration)

    def _get_oauth_token(self, integration: Integration) -> str:
        # Check expiry, refresh if needed, return token

    def _get_manual_token(self, integration: Integration) -> str:
        # Check virtual expiration cache, return token
```

### Integration Model Enhancement
```python
class JiraIntegration(Base):
    token_source = Column(String, nullable=False, default='oauth')

    @property
    def is_oauth(self) -> bool:
        return self.token_source == 'oauth'

    @property
    def is_manual(self) -> bool:
        return self.token_source == 'manual'

    @property
    def supports_refresh(self) -> bool:
        return self.is_oauth
```

### Encryption Consistency
- Use existing `encrypt_token()` and `decrypt_token()` utilities
- Apply to both OAuth access_token and manual API tokens
- Store encrypted value in same field (access_token column)
- Encryption key from ENCRYPTION_KEY environment variable

## Deferred Ideas

### Performance Optimization
- Add index on token_source if query performance becomes issue
- Consider composite index (organization_id, token_source) if needed
- Defer until Phase 2 when validation patterns are clear

### Platform-Specific TokenManagers
- Defer creating JiraTokenManager, LinearTokenManager until needed
- Start with unified TokenManager, split only if platform differences emerge
- Phase 3 and 4 will clarify platform-specific needs

### Token Rotation Tracking
- Track when manual tokens were last validated
- Track validation failure patterns
- Defer to Phase 5 (User Experience) when method switching is implemented

### Advanced Error Handling
- Detailed error codes for different token failure types
- Retry logic for transient validation failures
- Defer to Phase 2 (Validation Infrastructure)

## Key Constraints from Project Context

1. **Encryption Parity Required:** Manual tokens MUST use same encryption as OAuth tokens (validated requirements from PROJECT.md)
2. **Existing Pattern Reuse:** Use existing IntegrationValidator service patterns (from research)
3. **No New Dependencies:** Use existing encryption utilities and FastAPI patterns (from research)
4. **Team-Level Access Trust:** Assume user provides tokens with correct team-level permissions (no programmatic permission verification)

## Success Criteria (from Roadmap)

1. ✓ API tokens stored with same Fernet encryption as OAuth tokens (ENCRYPTION_KEY)
2. ✓ Database models distinguish OAuth vs manual tokens via token_source field
3. ✓ TokenManager service provides get_valid_token() abstraction hiding OAuth refresh logic from API clients
4. ✓ Integration models expose is_oauth, is_manual, and supports_refresh properties
5. ✓ Encryption parity verified by security tests (no plaintext tokens)

All decisions and ideas in this document align with these success criteria.

---
*Context gathered: 2026-01-31*
*Ready for: Phase planning*
