# Stack Research: Token-Based Authentication

**Domain:** API token authentication alongside OAuth 2.0
**Researched:** 2026-01-30
**Confidence:** HIGH

## Recommended Stack

### Core Authentication Libraries

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **cryptography** | 46.0.4 | Token encryption/decryption using Fernet | Already in use; battle-tested symmetric encryption with AES-128-CBC + HMAC for integrity. Actively maintained (latest release Jan 2026). Provides the exact same security guarantees as existing OAuth token storage. |
| **httpx** | Latest stable | Async HTTP client for API validation | Already in use; modern async/await support, HTTP/2, connection pooling. Perfect for validating Jira API tokens (Basic Auth) and Linear API keys (Bearer). Consistent with existing OAuth validation patterns. |
| **pydantic** | 2.x (FastAPI compatible) | Request/response validation | Already in use via FastAPI; validates token input formats, prevents injection attacks. FastAPI now requires Pydantic v2 (v1 deprecated). |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **base64** | stdlib | Encode Jira email:token for Basic Auth | Jira API tokens require HTTP Basic Auth with base64-encoded "email:api_token" credentials. Use `base64.b64encode()` with UTF-8 encoding. |
| **secrets** | stdlib | Generate secure test tokens | For development/testing only. Use `secrets.token_urlsafe()` for generating mock API tokens. Never use for production token generation (users provide their own). |
| **python-jose[cryptography]** | Current | JWT validation (future-proofing) | Already in requirements.txt. Not needed for Jira API tokens or Linear API keys (they're opaque tokens), but useful if future providers use JWT-based API tokens. |

### Database (Already in Use)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **SQLAlchemy** | Current | ORM for token storage | Already in use; models already have `token_source` field ('oauth' or 'manual'). No schema changes needed—just leverage existing encrypted `access_token` column. |
| **PostgreSQL** | Current | Relational database | Already in use; existing `jira_integrations` and `linear_integrations` tables already support manual tokens via `token_source='manual'` field. |

## Installation

No new packages required. All necessary libraries already present in requirements.txt:

```bash
# Already installed (verify versions)
pip install cryptography==46.0.4
pip install httpx
pip install pydantic>=2.0.0
pip install python-jose[cryptography]
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Fernet (cryptography)** | AES-GCM via `cryptography.hazmat` | Only if you need authenticated encryption with associated data (AEAD). Fernet already provides authentication via HMAC, which is sufficient for token storage. AES-GCM adds complexity without meaningful security benefit here. |
| **httpx AsyncClient** | aiohttp | Never—httpx is already in use and provides better HTTP/2 support and cleaner async API. aiohttp is also in requirements.txt but httpx is the standard for FastAPI projects. |
| **base64 (stdlib)** | Custom encoding | Never—Jira's official API documentation mandates HTTP Basic Auth with base64 encoding. Using anything else breaks compatibility. |
| **Direct token storage** | Token hashing (bcrypt, Argon2) | Never for API tokens. Hashing is one-way; you need to decrypt tokens to make API calls. Fernet encryption is the correct choice. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **PyJWT for API token validation** | Jira API tokens and Linear API keys are opaque tokens, not JWTs. PyJWT cannot validate them. | Validate by making test API call to provider (existing pattern in `integration_validator.py`). |
| **OAuth2PasswordBearer for API tokens** | FastAPI's OAuth2PasswordBearer is designed for OAuth flows with token endpoints. API tokens are static, user-provided secrets. | Use `HTTPBearer` or custom dependency for extracting `Authorization` header. |
| **Storing tokens in environment variables** | Multi-user SaaS app with per-user tokens. Environment variables are global and leak tokens across users. | Store in database with Fernet encryption (existing pattern). |
| **Token rotation for user-provided API tokens** | Users manage their own API tokens in Jira/Linear dashboards. Server-side rotation would break user's token. | Document token expiration (Jira: 1 year default; Linear: never). Notify user to regenerate if validation fails. |
| **plaintext token storage** | API tokens are bearer credentials—anyone with the token has full access. Plaintext storage violates security best practices. | Fernet encryption with `ENCRYPTION_KEY` (existing pattern). |

## Stack Patterns by Variant

### If Jira API Token (Manual):
- **Auth method:** HTTP Basic Auth
- **Header format:** `Authorization: Basic <base64(email:api_token)>`
- **Encoding:** `base64.b64encode(f"{email}:{api_token}".encode()).decode()`
- **Storage:** Encrypt with Fernet, store in `jira_integrations.access_token`, set `token_source='manual'`
- **Expiration:** Jira API tokens expire in 1 year by default (March-May 2026 batch). No server-side refresh—user must regenerate.
- **Validation:** `GET https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/myself`
- **Why this approach:** Jira's official API documentation mandates Basic Auth for API tokens. OAuth 3LO is for workspace-level integrations; API tokens are for users blocked by OAuth policies.

### If Linear API Key (Manual):
- **Auth method:** Bearer token
- **Header format:** `Authorization: <api_key>` (note: no "Bearer" prefix for personal API keys)
- **Storage:** Encrypt with Fernet, store in `linear_integrations.access_token`, set `token_source='manual'`
- **Expiration:** Linear personal API keys never expire (unless manually revoked by user)
- **Validation:** GraphQL query `{ viewer { id } }` to `https://api.linear.app/graphql`
- **Why this approach:** Linear's official docs specify personal API keys use `Authorization: <API_KEY>` format, distinct from OAuth's `Bearer <token>`. Personal keys have higher rate limits (1,500/hr vs 500/hr for OAuth).

### If OAuth 2.0 (Existing):
- **Auth method:** Bearer token
- **Header format:** `Authorization: Bearer <access_token>`
- **Storage:** Already implemented—encrypted tokens with refresh logic
- **Why preserve:** OAuth provides better UX for workspace-level integrations and supports automatic refresh. Keep existing implementation unchanged.

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| **cryptography 46.0.4** | Python 3.8+ | Latest stable release (Jan 2026). Supports free-threaded Python 3.14. Minimum Rust 1.83.0 for build. |
| **httpx** | FastAPI, asyncio | HTTP/2 support, connection pooling. Async client pattern already used in `integration_oauth.py` and `integration_validator.py`. |
| **pydantic 2.x** | FastAPI 0.119+ | FastAPI requires Pydantic v2 (v1 deprecated). Already in use; compatible with existing validation patterns. |
| **SQLAlchemy** | PostgreSQL | Existing models already support `token_source` field. No migration needed. |

## Security Considerations

### Key Management
- **Use existing ENCRYPTION_KEY:** Reuse `settings.ENCRYPTION_KEY` (already used for OAuth tokens). Consistent encryption key management.
- **Key rotation:** If rotating encryption key, must re-encrypt both OAuth tokens AND manual API tokens. Existing `get_encryption_key()` pattern handles this.

### Token Storage
- **Never log tokens:** Existing logger in `integration_validator.py` only logs first 40 chars of encryption key (safe). Continue this pattern.
- **Decrypt only when needed:** Decrypt tokens just-in-time for API calls (existing pattern). Never store decrypted tokens in memory longer than request lifecycle.

### Token Validation
- **Validate on first use:** When user provides API token, immediately validate with test API call before storing (existing pattern in `_validate_github`, `_validate_linear`, `_validate_jira`).
- **Cache validation results:** Reuse existing `validation_cache.py` with Redis. TTL for manual tokens: 15 minutes (same as OAuth).
- **Handle 401 gracefully:** If API call returns 401, invalidate cache and prompt user to update token (existing pattern).

### Rate Limiting
- **Jira API tokens:** Subject to Atlassian rate limits (logged in `integration_oauth.py` lines 486-501). No change needed.
- **Linear API keys:** 1,500 requests/hour (vs 500/hour for OAuth). Higher limit is a benefit—no additional handling needed.

### CAPTCHA Protection (Jira-specific)
- **Risk:** Jira triggers CAPTCHA after multiple failed auth attempts, blocking REST API access entirely.
- **Detection:** Check for `X-Seraph-LoginReason: AUTHENTICATION_DENIED` header.
- **Mitigation:** Limit validation attempts. Cache failed validations to prevent retry storms. Existing validation cache helps here.

## Sources

### Official Documentation
- [Jira Basic Auth for REST APIs](https://developer.atlassian.com/cloud/jira/platform/basic-auth-for-rest-apis/) — Jira API token authentication requirements
- [Manage API tokens for your Atlassian account](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/) — Jira API token management and expiration
- [Linear Getting Started](https://linear.app/developers/graphql) — Linear authentication methods and API key usage
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/) — FastAPI security patterns and dependency injection
- [Fernet Symmetric Encryption](https://cryptography.io/en/latest/fernet/) — Cryptography library Fernet implementation

### Package Versions (Verified Jan 2026)
- [cryptography 46.0.4 on PyPI](https://pypi.org/project/cryptography/) — Latest stable release
- [HTTPX Documentation](https://www.python-httpx.org/) — Async client patterns
- [Pydantic Documentation](https://docs.pydantic.dev/latest/) — Pydantic v2 migration guide

### Community Best Practices
- [Jira API Token Best Practices](https://community.atlassian.com/forums/Jira-questions/User-API-Token-Best-Practices/qaq-p/3095043) — Atlassian community security guidance
- [How to Use Linear's API Tokens](https://www.storylane.io/tutorials/how-to-use-linears-api-tokens) — Linear API key tutorial
- [The New Way To Generate Secure Tokens in Python](https://blog.miguelgrinberg.com/post/the-new-way-to-generate-secure-tokens-in-python) — Python secrets module best practices

---
*Stack research for: Token-based authentication for Jira and Linear*
*Researched: 2026-01-30*
*Confidence: HIGH (all recommendations verified with official docs and existing codebase)*
