# Architecture Research: API Key Management for On-Call Health

**Domain:** API Key Authentication alongside OAuth/JWT
**Researched:** 2026-01-30
**Confidence:** HIGH

## System Overview

```
                         ┌──────────────────────────────────────────────────────────────────┐
                         │                    Frontend (Next.js)                            │
                         │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
                         │  │  Settings Page  │  │  API Key Modal  │  │  Key List View  │  │
                         │  │  (existing)     │  │  (new)          │  │  (new)          │  │
                         │  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘  │
                         │           │                    │                    │            │
                         └───────────┼────────────────────┼────────────────────┼────────────┘
                                     │                    │                    │
                                     ▼                    ▼                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FastAPI Backend                                              │
│                                                                                                 │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                            Authentication Layer                                            │ │
│  │  ┌─────────────────┐    ┌─────────────────────────────────────────────────────────────┐  │ │
│  │  │  HTTPBearer     │    │                 Unified Auth Dependency                     │  │ │
│  │  │  (existing)     │◄───┤  get_current_user_or_api_key() - NEW                        │  │ │
│  │  │                 │    │    ├─ Tries JWT token first (Authorization: Bearer <jwt>)   │  │ │
│  │  │  APIKeyHeader   │◄───┤    └─ Falls back to API key (X-API-Key: <key>)              │  │ │
│  │  │  (new)          │    │                                                             │  │ │
│  │  └─────────────────┘    └─────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                               API Endpoints                                                │ │
│  │  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────────────────┐  │ │
│  │  │  /api/keys         │  │  /api/keys/{id}    │  │  Protected Endpoints (existing)    │  │ │
│  │  │  POST (create)     │  │  DELETE (revoke)   │  │  • /rootly/*                       │  │ │
│  │  │  GET (list)        │  │  PATCH (update)    │  │  • /integrations/*                 │  │ │
│  │  └────────────────────┘  └────────────────────┘  │  • /analyses/*                     │  │ │
│  │                                                   │  • /mcp/* (server)                 │  │ │
│  │                                                   └────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                               Service Layer                                                │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                    ApiKeyService (NEW)                                               │  │ │
│  │  │    • create_api_key(user_id, name, scopes) -> (key_id, raw_key)                     │  │ │
│  │  │    • validate_api_key(raw_key) -> User | None                                        │  │ │
│  │  │    • list_api_keys(user_id) -> List[ApiKeyInfo]                                     │  │ │
│  │  │    • revoke_api_key(user_id, key_id)                                                │  │ │
│  │  │    • update_api_key(user_id, key_id, name)                                          │  │ │
│  │  │    • check_scope(api_key_id, required_scope) -> bool                                │  │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                               Model Layer                                                  │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                         ApiKey Model (NEW)                                           │  │ │
│  │  │    id, user_id, name, key_prefix, key_hash, scopes,                                 │  │ │
│  │  │    last_used_at, expires_at, is_active, created_at                                  │  │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘  │ │
│  │  ┌─────────────────────────────────────────────────────────────────────────────────────┐  │ │
│  │  │                       User Model (existing)                                          │  │ │
│  │  │    + api_keys relationship                                                          │  │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────┘  │ │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                              │                                                  │
│                                              ▼                                                  │
│  ┌───────────────────────────────────────────────────────────────────────────────────────────┐ │
│  │                             PostgreSQL Database                                            │ │
│  │  ┌───────────────────────────────────────────────────────────────────────────────────┐    │ │
│  │  │  api_keys table                                                                    │    │ │
│  │  │  ├─ id (PK)                                                                        │    │ │
│  │  │  ├─ user_id (FK -> users.id, indexed)                                              │    │ │
│  │  │  ├─ name (user-friendly identifier)                                                │    │ │
│  │  │  ├─ key_prefix (first 8 chars for identification: "och_xxxx...")                   │    │ │
│  │  │  ├─ key_hash (SHA-256 hash, indexed for fast lookup)                               │    │ │
│  │  │  ├─ scopes (JSON array: ["mcp:read", "mcp:write", "api:full"])                     │    │ │
│  │  │  ├─ last_used_at (timestamp)                                                       │    │ │
│  │  │  ├─ expires_at (nullable timestamp)                                                │    │ │
│  │  │  ├─ is_active (boolean, default true)                                              │    │ │
│  │  │  └─ created_at (timestamp)                                                         │    │ │
│  │  └───────────────────────────────────────────────────────────────────────────────────┘    │ │
│  └───────────────────────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| **ApiKey Model** | SQLAlchemy model defining api_keys table schema | Database, ApiKeyService |
| **ApiKeyService** | Business logic for key creation, validation, revocation | ApiKey Model, User Model |
| **Unified Auth Dependency** | FastAPI dependency that accepts JWT OR API key | JWT module, ApiKeyService |
| **API Key Endpoints** | CRUD operations for user's API keys | ApiKeyService, Auth dependencies |
| **MCP Auth** | Extracts authentication from MCP context | Unified Auth Dependency |
| **Frontend Key Management** | UI for creating, viewing, revoking keys | API Key Endpoints |

## Data Flow

### Key Creation Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────┐
│ Frontend │────►│ POST /api/   │────►│ ApiKeyService│────►│ Generate key  │────►│ Store hash │
│          │     │ keys         │     │ .create()    │     │ with secrets  │     │ in DB      │
└──────────┘     └──────────────┘     └──────────────┘     └───────────────┘     └────────────┘
                                              │
                                              ▼
                                     ┌───────────────────┐
                                     │ Return raw key    │
                                     │ (ONCE ONLY!)      │
                                     │ och_xxxxxxxxxxxx  │
                                     └───────────────────┘
```

**Security Note:** The raw API key is returned ONLY at creation time. It is never stored and cannot be retrieved later. Users must save it immediately.

### Key Validation Flow (API Request Authentication)

```
┌──────────────┐     ┌─────────────────────┐     ┌────────────────────┐     ┌──────────────────┐
│ API Request  │────►│ Unified Auth        │────►│ Check X-API-Key    │────►│ Hash key with    │
│ X-API-Key:   │     │ Dependency          │     │ header present?    │     │ SHA-256          │
│ och_xxx...   │     └─────────────────────┘     └────────────────────┘     └──────────────────┘
└──────────────┘                                          │                          │
                                                          │ Yes                      │
                                                          ▼                          ▼
                                              ┌────────────────────┐     ┌──────────────────┐
                                              │ Query api_keys     │◄────│ Compare hash     │
                                              │ WHERE key_hash =   │     │ with DB          │
                                              │ AND is_active=true │     │                  │
                                              └────────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────┐     ┌──────────────────┐
                                              │ Load User via      │────►│ Update           │
                                              │ user_id            │     │ last_used_at     │
                                              └────────────────────┘     └──────────────────┘
                                                          │
                                                          ▼
                                              ┌────────────────────┐
                                              │ Return User +      │
                                              │ API Key context    │
                                              └────────────────────┘
```

### MCP Server Authentication Flow (Primary Use Case)

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│ Claude Desktop   │────►│ MCP Transport    │────►│ mcp/auth.py      │────►│ Unified Auth     │
│ or other client  │     │ (SSE/stdio)      │     │ require_user()   │     │ Dependency       │
│                  │     │ Authorization:   │     │                  │     │                  │
│                  │     │ Bearer och_xxx   │     │                  │     │                  │
└──────────────────┘     └──────────────────┘     └──────────────────┘     └──────────────────┘
                                                                                    │
                                                                                    ▼
                                                                         ┌──────────────────┐
                                                                         │ JWT? Try first   │
                                                                         │ API Key? Fallback│
                                                                         │ → User object    │
                                                                         └──────────────────┘
```

## Recommended Project Structure

```
backend/app/
├── auth/                          # Authentication module (existing)
│   ├── __init__.py
│   ├── dependencies.py            # MODIFY: Add unified auth dependency
│   ├── jwt.py                     # JWT handling (existing)
│   ├── oauth.py                   # OAuth providers (existing)
│   └── api_key.py                 # NEW: API key authentication utilities
├── models/                        # Database models (existing)
│   ├── __init__.py                # MODIFY: Export ApiKey
│   ├── user.py                    # MODIFY: Add api_keys relationship
│   └── api_key.py                 # NEW: ApiKey model
├── services/                      # Business logic (existing)
│   └── api_key_service.py         # NEW: API key service
├── api/
│   └── endpoints/
│       └── api_keys.py            # NEW: API key CRUD endpoints
└── mcp/
    ├── auth.py                    # MODIFY: Use unified auth
    └── server.py                  # MCP server (existing)

frontend/src/
├── app/
│   └── settings/
│       └── api-keys/              # NEW: API key management page
│           └── page.tsx
└── components/
    └── settings/
        └── api-keys/              # NEW: API key components
            ├── api-key-list.tsx
            ├── create-key-modal.tsx
            └── key-display.tsx
```

### Structure Rationale

- **`auth/api_key.py`:** Separate API key utilities from JWT to keep concerns isolated while sharing the auth module namespace
- **`models/api_key.py`:** Follow existing model pattern (one model per file)
- **`services/api_key_service.py`:** Follow existing service pattern for business logic
- **`api/endpoints/api_keys.py`:** Follow existing endpoint pattern for CRUD operations
- **Frontend in settings:** API keys are a user setting, so they belong in the settings section alongside existing integrations

## Architectural Patterns

### Pattern 1: Unified Authentication Dependency

**What:** A single FastAPI dependency that tries multiple authentication methods in order (JWT first, then API key).

**When to use:** When endpoints should accept either authentication method transparently.

**Trade-offs:**
- Pro: Endpoints don't need to know which auth method was used
- Pro: Easy to extend with additional auth methods
- Con: Slightly more complex dependency code

**Example:**
```python
# backend/app/auth/dependencies.py

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, APIKeyHeader

http_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_current_user_or_api_key(
    request: Request,
    bearer_token: Optional[str] = Depends(http_bearer),
    api_key: Optional[str] = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Unified auth dependency.
    1. Try JWT token from Authorization header
    2. Fall back to API key from X-API-Key header
    """
    # Try JWT first (existing behavior)
    if bearer_token:
        user = await _validate_jwt(bearer_token.credentials, db)
        if user:
            return user

    # Try cookie token (existing behavior for web app)
    cookie_token = request.cookies.get("auth_token")
    if cookie_token:
        user = await _validate_jwt(cookie_token, db)
        if user:
            return user

    # Try API key
    if api_key:
        user = await _validate_api_key(api_key, db)
        if user:
            return user

    raise HTTPException(status_code=401, detail="Not authenticated")
```

### Pattern 2: Hash-Based Key Storage

**What:** Store only a SHA-256 hash of the API key, never the raw key itself.

**When to use:** Always. API keys should never be stored in plaintext.

**Trade-offs:**
- Pro: Even if database is compromised, keys cannot be extracted
- Pro: Fast lookup using indexed hash
- Con: Cannot show full key to user after creation (feature, not bug)

**Example:**
```python
# backend/app/services/api_key_service.py

import hashlib
import secrets

class ApiKeyService:
    KEY_PREFIX = "och_"  # On-Call Health prefix for easy identification

    def create_api_key(self, db: Session, user_id: int, name: str) -> tuple[int, str]:
        """
        Create a new API key.
        Returns: (key_id, raw_key) - raw_key is shown once and never stored
        """
        # Generate cryptographically secure random key
        random_part = secrets.token_urlsafe(32)
        raw_key = f"{self.KEY_PREFIX}{random_part}"

        # Hash for storage (never store the raw key)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        # Store prefix for UI identification
        key_prefix = raw_key[:12]  # "och_" + first 8 chars

        api_key = ApiKey(
            user_id=user_id,
            name=name,
            key_prefix=key_prefix,
            key_hash=key_hash,
            is_active=True
        )
        db.add(api_key)
        db.commit()

        return api_key.id, raw_key  # Return raw key ONCE

    def validate_api_key(self, db: Session, raw_key: str) -> Optional[User]:
        """Validate an API key and return the associated user."""
        if not raw_key or not raw_key.startswith(self.KEY_PREFIX):
            return None

        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

        api_key = db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True
        ).first()

        if not api_key:
            return None

        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Update last used timestamp
        api_key.last_used_at = datetime.utcnow()
        db.commit()

        return api_key.user
```

### Pattern 3: Prefix-Based Key Identification

**What:** Include a recognizable prefix (e.g., `och_`) in API keys for easy identification.

**When to use:** Standard practice for API key design. Helps users and security tools identify key types.

**Trade-offs:**
- Pro: Users can easily identify On-Call Health keys
- Pro: Security scanners can detect exposed keys
- Pro: Enables quick visual verification in logs
- Con: Slightly shorter entropy (minimal impact with 32+ bytes of random data)

**Example Keys:**
- `och_xk7Yz...` - On-Call Health API key
- Similar to: `sk-...` (OpenAI), `ghp_...` (GitHub), `rk_...` (Stripe)

## Anti-Patterns

### Anti-Pattern 1: Storing Raw API Keys

**What people do:** Store the actual API key in the database (encrypted or not).

**Why it's wrong:**
- If encryption key is compromised, all API keys are exposed
- Database backups contain usable credentials
- Unnecessary attack surface

**Do this instead:** Store only SHA-256 hash. Key is shown once at creation, never stored.

### Anti-Pattern 2: Using JWT for Long-Lived Machine Tokens

**What people do:** Create JWT tokens with very long expiration for MCP/programmatic access.

**Why it's wrong:**
- JWTs cannot be revoked without token blocklist
- Long-lived JWTs accumulate if user creates many
- No way to track "which token did what"

**Do this instead:** Use revocable API keys with audit trail (last_used_at, name).

### Anti-Pattern 3: Global API Key (No User Binding)

**What people do:** Create shared API keys not associated with specific users.

**Why it's wrong:**
- No audit trail of which user performed actions
- Cannot revoke access for specific users
- Violates principle of least privilege

**Do this instead:** Each API key belongs to exactly one user. User's permissions apply to their keys.

### Anti-Pattern 4: Returning Key on GET Requests

**What people do:** Allow users to retrieve their API key value after creation.

**Why it's wrong:**
- Increases exposure window
- If someone gains temporary read access, they get permanent API access
- Encourages insecure storage habits

**Do this instead:** Show raw key ONCE at creation with prominent "save now" warning. Only show prefix (e.g., `och_xk7Y...`) in subsequent views.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Claude Desktop / MCP Clients | X-API-Key header or Authorization: Bearer | Primary use case for API keys |
| CI/CD Pipelines | X-API-Key header | Automated analysis runs |
| Third-party integrations | X-API-Key header | Any programmatic access |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Auth ↔ Models | Direct import | ApiKey model used by auth dependency |
| Auth ↔ Services | Dependency injection | ApiKeyService validates keys |
| Endpoints ↔ Services | Dependency injection | Standard FastAPI pattern |
| MCP ↔ Auth | Direct import | `require_user()` uses unified auth |

## Suggested Build Order

Based on dependencies and the existing codebase patterns, the recommended implementation order is:

### Phase 1: Backend Foundation (Model + Service)

**What to build:**
1. `models/api_key.py` - SQLAlchemy model
2. Database migration (Alembic)
3. `services/api_key_service.py` - Business logic
4. Unit tests for service

**Why first:** Everything else depends on the data model and core business logic.

**Integration points:** Add `api_keys` relationship to User model in `models/user.py`.

### Phase 2: Authentication Middleware

**What to build:**
1. `auth/api_key.py` - API key validation utilities
2. Modify `auth/dependencies.py` - Unified auth dependency
3. Modify `mcp/auth.py` - Use unified auth for MCP
4. Integration tests for auth flow

**Why second:** Auth middleware must work before endpoints can use it.

**Integration points:**
- `get_current_user_or_api_key()` replaces `get_current_user()` where API key access is desired
- MCP `require_user()` gains API key support transparently

### Phase 3: API Endpoints

**What to build:**
1. `api/endpoints/api_keys.py` - CRUD endpoints
2. Register router in `main.py`
3. API endpoint tests

**Why third:** Endpoints need working auth and service layer.

**Endpoints:**
- `POST /api/keys` - Create new key
- `GET /api/keys` - List user's keys (shows prefix only)
- `DELETE /api/keys/{id}` - Revoke key
- `PATCH /api/keys/{id}` - Update name

### Phase 4: Frontend UI

**What to build:**
1. API key list component
2. Create key modal (with "copy and save" UX)
3. Settings page integration
4. E2E tests

**Why last:** Frontend depends on working backend API.

**Integration points:** Add to existing settings page, similar to integration management UI.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-1k users | Current architecture is sufficient. SHA-256 hash lookup is fast with index. |
| 1k-100k users | Consider caching validated keys in Redis (TTL ~5 minutes) to reduce DB load |
| 100k+ users | Rate limiting per API key, key usage analytics, separate read replica for key validation |

### Scaling Priorities

1. **First bottleneck:** Database lookups per request. Mitigate with indexed `key_hash` column (included in design).
2. **Second bottleneck:** If API key validation becomes hot path, add Redis cache layer for recently-used keys.

## Security Considerations

### Key Format
- Prefix: `och_` (On-Call Health identifier)
- Random part: 32 bytes from `secrets.token_urlsafe()` = ~256 bits entropy
- Total: ~47 characters (e.g., `och_xk7Yz9AB...`)

### Storage
- Raw key: Never stored, shown once at creation
- Stored: SHA-256 hash (64 hex chars)
- Prefix: First 12 chars for UI identification (`och_xk7Y...`)

### Validation
- Constant-time comparison via `secrets.compare_digest()` for hash comparison
- No timing attacks possible

### Revocation
- Immediate: Set `is_active = False`
- No blocklist needed (unlike JWT)

### Expiration (Optional)
- `expires_at` column allows time-limited keys
- Validated on every request

## Sources

- [FastAPI Security Documentation](https://fastapi.tiangolo.com/tutorial/security/)
- [FastAPI API Key Authentication - TestDriven.io](https://testdriven.io/tips/6840e037-4b8f-4354-a9af-6863fb1c69eb/)
- [API Key Authentication Best Practices - Zuplo](https://zuplo.com/blog/2022/12/01/api-key-authentication)
- [Best Practices for Building Secure API Keys - Bomberbot](https://www.bomberbot.com/api/best-practices-for-building-secure-api-keys-a-comprehensive-guide/)
- [Google Cloud API Keys Best Practices](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices)
- Existing On-Call Health codebase patterns (auth/, models/, services/)

---
*Architecture research for: API Key Management in On-Call Health*
*Researched: 2026-01-30*
