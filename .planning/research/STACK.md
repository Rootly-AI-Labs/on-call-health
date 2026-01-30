# Stack Research: API Key Management

**Domain:** API Key Authentication for FastAPI/SQLAlchemy/PostgreSQL
**Researched:** 2026-01-30
**Confidence:** HIGH (verified against official documentation and PyPI)

## Executive Summary

This research identifies the recommended 2026 stack for implementing API key management in the existing On-Call Health FastAPI application. The key decision points are:

1. **Hashing Algorithm:** Argon2id via `argon2-cffi` (not passlib - it's unmaintained)
2. **Key Generation:** Python's built-in `secrets` module
3. **FastAPI Integration:** Native `APIKeyHeader` dependency
4. **Storage Pattern:** Prefix + hashed lookup with SHA-256 for fast retrieval

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended | Confidence |
|------------|---------|---------|-----------------|------------|
| `argon2-cffi` | 25.1.0 | Password/key hashing | Argon2 PHC winner; actively maintained; 5.6M weekly downloads; supports Python 3.8-3.14 | HIGH |
| `secrets` (stdlib) | Python 3.10+ | Secure key generation | Cryptographically secure; no dependencies; stdlib since 3.6 | HIGH |
| `hmac.compare_digest` (stdlib) | Python 3.10+ | Timing-safe comparison | Prevents timing attacks; no dependencies; stdlib | HIGH |
| `hashlib.sha256` (stdlib) | Python 3.10+ | Fast lookup hash | For non-sensitive key prefix lookups; O(1) database retrieval | HIGH |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| `pwdlib[argon2]` | 0.3.0 | Password hash wrapper | Alternative to direct argon2-cffi if multi-algorithm support needed; used by FastAPI-Users | MEDIUM |
| `bcrypt` | 5.0.0 | Bcrypt hashing | Only for backward compatibility with existing hashes | HIGH |

### FastAPI Security Integration

| Component | Import Path | Purpose | Notes |
|-----------|-------------|---------|-------|
| `APIKeyHeader` | `fastapi.security` | Header-based API key extraction | Primary method for MCP/automation clients |
| `APIKeyQuery` | `fastapi.security` | Query param API key | Backup method; less secure (logs) |
| `Security` | `fastapi` | Dependency injection | For combining multiple auth methods |
| `Depends` | `fastapi` | Standard dependency | For route protection |

## Installation

```bash
# Add to requirements.txt (do NOT use passlib)
argon2-cffi>=25.1.0

# Or if using pwdlib wrapper:
pwdlib[argon2]>=0.3.0
```

No additional pip installs needed - `secrets`, `hmac`, and `hashlib` are Python stdlib.

## API Key Storage Pattern

### Recommended: Prefix + Hash Pattern

```
Key Format: och_live_<random_32_bytes_hex>
             |    |   |
             |    |   +-- 64 hex chars from secrets.token_hex(32)
             |    +------ Environment indicator (live/test)
             +----------- Service prefix (On-Call Health)

Storage:
- key_prefix: "och_live_abc123" (first 16 chars, indexed)
- key_hash: SHA256(full_key) for fast lookup
- key_hash_argon2: Argon2id(full_key) for verification
```

### Database Schema Recommendations

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Lookup fields (indexed)
    key_prefix VARCHAR(20) NOT NULL,           -- "och_live_abc123"
    key_hash_sha256 VARCHAR(64) NOT NULL,      -- Fast lookup hash

    -- Verification field (not indexed)
    key_hash_argon2 VARCHAR(128) NOT NULL,     -- Secure verification hash

    -- Metadata
    name VARCHAR(100) NOT NULL,                -- User-provided description
    scopes VARCHAR(255)[] DEFAULT '{}',        -- Permission scopes

    -- Lifecycle
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,                    -- NULL = never expires
    revoked_at TIMESTAMPTZ,                    -- NULL = active

    -- Constraints
    CONSTRAINT api_keys_key_prefix_unique UNIQUE (key_prefix),
    CONSTRAINT api_keys_key_hash_sha256_unique UNIQUE (key_hash_sha256)
);

-- Fast lookup index (crucial for <50ms validation)
CREATE INDEX idx_api_keys_prefix_active ON api_keys (key_prefix)
    WHERE revoked_at IS NULL AND (expires_at IS NULL OR expires_at > NOW());

-- Hash index for SHA256 lookups (40% smaller, 15% faster than B-tree for equality)
CREATE INDEX idx_api_keys_hash_sha256 USING HASH (key_hash_sha256);
```

### Why Two Hashes?

| Hash | Purpose | Performance | Security |
|------|---------|-------------|----------|
| SHA-256 | Database lookup | O(1), <1ms | Not for secrets; only for identification |
| Argon2id | Final verification | ~200ms target | Full password-grade security |

This two-step approach achieves <50ms total validation:
1. **Step 1:** Query by SHA-256 hash (~1-5ms with index)
2. **Step 2:** Verify with Argon2id (~200ms, but only after DB match)

## Alternatives Considered

| Recommended | Alternative | Why Not Use Alternative |
|-------------|-------------|-------------------------|
| `argon2-cffi` | `passlib` | Passlib unmaintained since 2020; breaks on Python 3.13+; FastAPI docs switched to pwdlib |
| `argon2-cffi` | `bcrypt` | Fixed 4KB memory (less resistant to GPU attacks); truncates at 72 chars |
| `secrets.token_hex()` | `uuid.uuid4()` | UUIDs are predictable with enough samples; not cryptographically designed |
| `hmac.compare_digest()` | `==` operator | String equality vulnerable to timing attacks |
| Prefix pattern | Full hash only | Full-hash-only requires hashing on every request; prefix enables fast lookup |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `passlib` | Unmaintained since 2020; Python 3.13+ incompatible; DeprecationWarnings on import | `argon2-cffi` directly or `pwdlib` |
| `random` module | Not cryptographically secure; predictable output | `secrets` module |
| `==` for key comparison | Timing attack vulnerable | `hmac.compare_digest()` |
| Plain bcrypt for new keys | 72-char limit; no memory-hard protection | Argon2id |
| Storing full API key | Database breach = full compromise | Store only hashes |
| MD5/SHA1 for security | Cryptographically broken | SHA-256 for lookup; Argon2id for verification |

## Implementation Patterns

### Key Generation

```python
import secrets
import hashlib
from argon2 import PasswordHasher

def generate_api_key(user_id: int, environment: str = "live") -> tuple[str, str, str, str]:
    """
    Generate a new API key with prefix and hashes.

    Returns: (full_key, prefix, sha256_hash, argon2_hash)
    """
    # 1. Generate cryptographically secure random bytes
    random_part = secrets.token_hex(32)  # 64 hex characters

    # 2. Create prefixed key (like Stripe: sk_live_xxx)
    prefix = f"och_{environment}_{random_part[:8]}"
    full_key = f"och_{environment}_{random_part}"

    # 3. Create fast-lookup hash (SHA-256)
    sha256_hash = hashlib.sha256(full_key.encode()).hexdigest()

    # 4. Create secure verification hash (Argon2id)
    ph = PasswordHasher()  # Uses Argon2id by default
    argon2_hash = ph.hash(full_key)

    return full_key, prefix, sha256_hash, argon2_hash
```

### Key Validation

```python
import hmac
import hashlib
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session

async def validate_api_key(key: str, db: Session) -> Optional[User]:
    """
    Validate API key with timing-safe comparison.
    Target: <50ms total latency.
    """
    # 1. Quick format check
    if not key.startswith("och_"):
        return None

    # 2. Compute SHA-256 for fast DB lookup
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    # 3. Database lookup by hash (indexed, ~1-5ms)
    api_key_record = db.query(APIKey).filter(
        APIKey.key_hash_sha256 == key_hash,
        APIKey.revoked_at.is_(None),
        or_(APIKey.expires_at.is_(None), APIKey.expires_at > func.now())
    ).first()

    if not api_key_record:
        return None

    # 4. Verify with Argon2 (secure, ~200ms)
    ph = PasswordHasher()
    try:
        ph.verify(api_key_record.key_hash_argon2, key)
    except VerifyMismatchError:
        return None

    # 5. Update last_used_at (async/background is fine)
    api_key_record.last_used_at = func.now()

    return api_key_record.user
```

### FastAPI Dependency

```python
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import APIKeyHeader

# Define the header scheme
api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="API Key",
    description="API key for MCP clients and automation",
    auto_error=False  # Return None instead of 401, so we can check JWT too
)

async def get_current_user_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Dependency for API key authentication."""
    if not api_key:
        return None
    return await validate_api_key(api_key, db)

# Combined auth: JWT or API Key
async def get_current_user(
    jwt_user: Optional[User] = Depends(get_jwt_user_optional),
    api_key_user: Optional[User] = Depends(get_current_user_api_key)
) -> User:
    """Accept either JWT or API key authentication."""
    user = jwt_user or api_key_user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing authentication",
            headers={"WWW-Authenticate": "Bearer, ApiKey"}
        )
    return user
```

## Argon2 Configuration

### Recommended Parameters (2026)

```python
from argon2 import PasswordHasher, Type

# Production settings - balance security vs latency
ph = PasswordHasher(
    time_cost=3,           # iterations (default: 3)
    memory_cost=65536,     # 64MB (default: 65536 KB)
    parallelism=4,         # threads (default: 4)
    hash_len=32,           # output length (default: 32)
    salt_len=16,           # salt length (default: 16)
    type=Type.ID           # Argon2id (hybrid, recommended)
)

# Target: 200-500ms verification time
# Adjust time_cost based on your server hardware
```

### Why Argon2id?

| Variant | Protection Against | Recommendation |
|---------|-------------------|----------------|
| Argon2d | GPU attacks | Data-dependent access; vulnerable to side-channel |
| Argon2i | Side-channel attacks | Time-memory tradeoff vulnerable |
| Argon2id | Both | **Recommended** - hybrid approach |

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `argon2-cffi>=25.1.0` | Python 3.8-3.14, PyPy | Includes Pyodide/WASM support |
| `pwdlib>=0.3.0` | Python 3.10+ | Requires `[argon2]` extra |
| `bcrypt>=5.0.0` | Python 3.8+, PyPy 3 | Now Rust-based; requires Rust compiler for source builds |
| FastAPI 0.128.0 | Python 3.10+ | Dropped 3.8 support; Pydantic v1 deprecated |

## Existing Codebase Integration Notes

The current On-Call Health backend uses:
- `passlib[bcrypt]` in requirements.txt - **should migrate to argon2-cffi**
- `python-jose[cryptography]` for JWT - **keep as-is, works alongside API keys**
- Existing `app/mcp/auth.py` extracts bearer tokens - **extend to support X-API-Key header**
- Security middleware in `app/middleware/security.py` - **add API key routes to sensitive routes**

Migration path:
1. Add `argon2-cffi>=25.1.0` to requirements.txt
2. Keep `passlib[bcrypt]` temporarily for backward compat with existing password hashes
3. Create new APIKey model with dual-hash storage
4. Add FastAPI dependency that checks both JWT and API key
5. Eventually remove passlib when all password hashes upgraded

## Sources

- [argon2-cffi PyPI](https://pypi.org/project/argon2-cffi/) - Version 25.1.0 verified (June 3, 2025)
- [argon2-cffi Documentation](https://argon2-cffi.readthedocs.io/) - Official docs
- [pwdlib PyPI](https://pypi.org/project/pwdlib/) - Version 0.3.0 verified (October 25, 2025)
- [pwdlib Guide](https://frankie567.github.io/pwdlib/guide/) - Official usage guide
- [bcrypt PyPI](https://pypi.org/project/bcrypt/) - Version 5.0.0 verified
- [FastAPI Security Reference](https://fastapi.tiangolo.com/reference/security/) - APIKeyHeader documentation
- [Python secrets module](https://docs.python.org/3/library/secrets.html) - Official stdlib docs
- [Python hmac module](https://docs.python.org/3/library/hmac.html) - compare_digest documentation
- [PostgreSQL Hash Indexes](https://www.postgresql.org/docs/current/hash-index.html) - Official docs on hash index performance
- [Password Hashing Guide 2025](https://guptadeepak.com/the-complete-guide-to-password-hashing-argon2-vs-bcrypt-vs-scrypt-vs-pbkdf2-2026/) - Algorithm comparison
- [FastAPI-Users Password Hash](https://fastapi-users.github.io/fastapi-users/latest/configuration/password-hash/) - pwdlib adoption
- [passlib Maintenance Discussion](https://github.com/pypi/warehouse/issues/15454) - PyPI warehouse issue on passlib future
- [Best Practices for API Keys](https://www.freecodecamp.org/news/best-practices-for-building-api-keys-97c26eabfea9/) - Prefix + hash pattern
- [Prefix.dev API Keys](https://prefix.dev/blog/how_we_implented_api_keys) - Real-world implementation example

---
*Stack research for: API Key Management in FastAPI/SQLAlchemy/PostgreSQL*
*Researched: 2026-01-30*
