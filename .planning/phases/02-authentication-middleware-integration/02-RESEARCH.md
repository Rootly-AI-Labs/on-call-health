# Phase 2: Authentication Middleware Integration - Research

**Researched:** 2026-01-30
**Domain:** FastAPI Authentication Middleware - Dual Auth (JWT + API Key) with Rate Limiting
**Confidence:** HIGH

## Summary

This research investigated how to extend the existing authentication system to support both JWT tokens (for web OAuth sessions) and API keys (for programmatic/MCP access). The existing codebase has well-established patterns in `/backend/app/auth/dependencies.py` for JWT authentication using FastAPI's dependency injection system, and the Phase 1 work in `/backend/app/services/api_key_service.py` provides the core API key validation logic.

The key architectural decision from CONTEXT.md is **clean separation by use case**: MCP endpoints accept API keys ONLY (reject JWT), and web endpoints accept JWT ONLY (reject API keys). This simplifies implementation significantly - no complex precedence logic needed.

The existing rate limiting infrastructure in `/backend/app/core/rate_limiting.py` uses `slowapi` with Redis storage. Per-key rate limiting can be implemented by extending the existing `get_rate_limit_key()` function to return `api_key:{key_id}` for API key requests, giving each key an independent 100 req/min bucket.

**Primary recommendation:** Create a new `get_current_user_from_api_key` dependency that mirrors `get_current_user` but validates API keys instead of JWT. For MCP endpoints, use this dependency exclusively. Extend `get_rate_limit_key()` to identify requests by API key ID when present.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi.security.APIKeyHeader | existing | Extract API key from header | FastAPI built-in, integrates with OpenAPI |
| slowapi | existing | Rate limiting with Redis | Already in use for auth endpoints |
| hmac.compare_digest | stdlib | Timing-safe comparison | Python stdlib, prevents timing attacks |
| argon2-cffi | 25.1.0 | API key verification | Already installed from Phase 1 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fastapi.BackgroundTasks | existing | Async last_used_at updates | Fire-and-forget timestamp updates |
| asyncio.to_thread | stdlib | Non-blocking Argon2 verification | CPU-intensive hash verification |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| APIKeyHeader | Custom header parsing | APIKeyHeader integrates with OpenAPI docs automatically |
| BackgroundTasks | asyncio.create_task | BackgroundTasks is more reliable for DB operations |
| slowapi | fastapi-limiter | slowapi already integrated, no migration needed |

**Installation:**
No new dependencies needed - all libraries already installed from Phase 1 and existing codebase.

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── auth/
│   │   ├── dependencies.py      # Existing JWT deps + new API key deps
│   │   └── api_key_auth.py      # NEW: API key authentication logic
│   ├── mcp/
│   │   ├── auth.py              # Update: use API key auth for MCP
│   │   └── server.py            # Update: integrate new auth
│   └── core/
│       └── rate_limiting.py     # Update: per-key rate limiting
└── tests/
    └── test_api_key_auth.py     # NEW: Authentication middleware tests
```

### Pattern 1: Separate Authentication Dependencies
**What:** Create distinct dependencies for JWT and API key authentication that never mix
**When to use:** Per CONTEXT.md decision - clean separation by use case
**Why:** Prevents confusion about which auth method is valid, simplifies error messages

**Example:**
```python
# Source: FastAPI Security docs + existing backend/app/auth/dependencies.py pattern
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import APIKeyHeader

# API key header scheme - X-API-Key is the conventional header name
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # We'll handle errors ourselves for better messages
    description="API key for programmatic access"
)

async def get_current_user_from_api_key(
    request: Request,
    api_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from API key authentication.
    For MCP endpoints ONLY - rejects if JWT present.
    """
    # Check for JWT - if present, reject with helpful error
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires API key authentication, not JWT. Use X-API-Key header."
        )

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Validate and return user (see Pattern 2)
    user, api_key_model = await validate_api_key(api_key, db)

    # Store key ID in request state for rate limiting
    request.state.api_key_id = api_key_model.id

    return user
```

### Pattern 2: Two-Phase API Key Validation (<50ms)
**What:** SHA-256 lookup first (O(1)), then Argon2 verification (timing-safe)
**When to use:** All API key validation to meet <50ms latency requirement
**Why:** Phase 1 dual-hash pattern enables fast lookup with secure verification

**Example:**
```python
# Source: Phase 1 research + existing api_key_service.py
import asyncio
from app.services.api_key_service import compute_sha256_hash, verify_api_key
from app.models import APIKey

async def validate_api_key(
    key: str,
    db: Session
) -> tuple[User, APIKey]:
    """
    Validate API key and return (user, api_key_model).

    Phase 1: SHA-256 lookup (fast, indexed)
    Phase 2: Argon2 verification (timing-safe)

    Raises HTTPException with specific error messages per CONTEXT.md
    """
    # Phase 1: Fast lookup via SHA-256
    sha256_hash = compute_sha256_hash(key)
    api_key_model = db.query(APIKey).filter(
        APIKey.key_hash_sha256 == sha256_hash
    ).first()

    if not api_key_model:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Check revocation (before expensive Argon2 verification)
    if api_key_model.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"API key has been revoked",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Check expiration (before expensive Argon2 verification)
    if api_key_model.expires_at is not None:
        from datetime import datetime, timezone
        if datetime.now(timezone.utc) >= api_key_model.expires_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API key expired on {api_key_model.expires_at.strftime('%Y-%m-%d')}",
                headers={"WWW-Authenticate": "APIKey"}
            )

    # Phase 2: Argon2 verification (run in thread pool to avoid blocking)
    is_valid = await asyncio.to_thread(
        verify_api_key, key, api_key_model.key_hash_argon2
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Load user
    user = db.query(User).filter(User.id == api_key_model.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key owner not found",
            headers={"WWW-Authenticate": "APIKey"}
        )

    return user, api_key_model
```

### Pattern 3: Async Last-Used Update
**What:** Update last_used_at timestamp without blocking the response
**When to use:** Every successful API key authentication (REQ-NF-003)
**Why:** Don't add latency to every request for non-critical timestamp update

**Example:**
```python
# Source: FastAPI BackgroundTasks docs + existing codebase patterns
from fastapi import BackgroundTasks
from datetime import datetime, timezone

def update_last_used_background(api_key_id: int, db_session_factory):
    """Background task to update last_used_at timestamp."""
    db = db_session_factory()
    try:
        api_key = db.query(APIKey).filter(APIKey.id == api_key_id).first()
        if api_key:
            api_key.last_used_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()

# In the dependency, schedule background task:
async def get_current_user_from_api_key(
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    # ... validation logic ...

    # Schedule async last_used update (fire and forget)
    background_tasks.add_task(
        update_last_used_background,
        api_key_model.id,
        SessionLocal  # Pass factory, not session (for thread safety)
    )

    return user
```

### Pattern 4: Per-Key Rate Limiting
**What:** Extend existing slowapi setup to use API key ID as rate limit key
**When to use:** All MCP endpoints (100 req/min per key)
**Why:** Prevents abuse while giving each key independent quota

**Example:**
```python
# Source: Existing rate_limiting.py + slowapi docs
def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on authentication context.
    Priority: API key ID > authenticated user ID > IP address
    """
    # Check for API key ID (set by API key auth dependency)
    if hasattr(request.state, "api_key_id"):
        return f"api_key:{request.state.api_key_id}"

    # Check for authenticated user ID (set by JWT auth)
    if hasattr(request.state, "user_id"):
        return f"user:{request.state.user_id}"

    # Fallback to IP address
    return get_remote_address(request)

# Rate limit configuration for MCP endpoints
RATE_LIMITS = {
    # ... existing limits ...
    "mcp_api_key": "100/minute",  # Per API key limit
}
```

### Pattern 5: MCP Auth Integration
**What:** Update MCP `require_user` to use API key authentication
**When to use:** All MCP tool/resource handlers
**Why:** MCP endpoints should only accept API keys per CONTEXT.md

**Example:**
```python
# Source: Existing backend/app/mcp/auth.py pattern
from app.auth.api_key_auth import validate_api_key_for_mcp

def require_user_from_api_key(ctx: Any, db: Session) -> User:
    """
    Require authenticated user from API key for MCP context.
    Extracts X-API-Key header from MCP context.
    """
    api_key = _extract_api_key(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    # Note: MCP handlers are sync, so use sync validation
    user, _ = validate_api_key_sync(api_key, db)
    return user

def _extract_api_key(ctx: Any) -> Optional[str]:
    """Extract X-API-Key from various MCP context shapes."""
    headers = getattr(ctx, "request_headers", None)
    if headers:
        return headers.get("X-API-Key") or headers.get("x-api-key")

    headers = getattr(ctx, "headers", None)
    if headers:
        return headers.get("X-API-Key") or headers.get("x-api-key")

    request = getattr(ctx, "request", None)
    if request:
        req_headers = getattr(request, "headers", None)
        if req_headers:
            return req_headers.get("X-API-Key") or req_headers.get("x-api-key")

    return None
```

### Anti-Patterns to Avoid
- **Mixing auth methods in one endpoint:** Keep JWT and API key endpoints completely separate
- **Using `==` for hash comparison:** Always use `hmac.compare_digest` or Argon2's built-in verification
- **Blocking async code with Argon2:** Always run `verify_api_key` in `asyncio.to_thread()`
- **Generic error messages when specific requested:** CONTEXT.md says reveal why key failed (expired, revoked)
- **Checking expiration/revocation after Argon2:** Check cheap conditions first, expensive verification last

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| API key extraction | Custom header parsing | `APIKeyHeader` | OpenAPI integration, standard behavior |
| Timing-safe comparison | String `==` operator | `hmac.compare_digest` | Timing attacks are real |
| Rate limiting | Custom counter logic | slowapi + Redis | Already integrated, battle-tested |
| Background tasks | Raw asyncio.create_task | BackgroundTasks | Better DB session handling |

**Key insight:** FastAPI's dependency injection system is the right abstraction for authentication. Don't try to share middleware between FastAPI and FastMCP (GitHub discussion shows state propagation issues) - use FastAPI dependencies for HTTP and custom auth for MCP context.

## Common Pitfalls

### Pitfall 1: Blocking Event Loop with Argon2
**What goes wrong:** Argon2 verification takes 50-100ms and blocks all concurrent requests
**Why it happens:** Argon2 is CPU-intensive by design (memory-hard function)
**How to avoid:** Always use `await asyncio.to_thread(verify_api_key, ...)`
**Warning signs:** High P99 latency during concurrent API requests

### Pitfall 2: Session Sharing Across Threads
**What goes wrong:** SQLAlchemy session used in background task causes "session is closed" errors
**Why it happens:** BackgroundTasks run after response, session may be closed
**How to avoid:** Pass session factory to background task, create new session inside
**Warning signs:** Intermittent "session is closed" or "object is not bound to session" errors

### Pitfall 3: FastMCP State Propagation
**What goes wrong:** Middleware sets `request.state.api_key_id` but MCP tools see empty state
**Why it happens:** FastMCP doesn't propagate ASGI scope state to tool context (see GitHub discussion #732)
**How to avoid:** Don't rely on middleware for MCP auth - extract API key directly in `require_user`
**Warning signs:** `AttributeError: 'State' object has no attribute 'api_key_id'`

### Pitfall 4: Race Condition on last_used_at
**What goes wrong:** Concurrent requests overwrite each other's last_used_at
**Why it happens:** Read-modify-write without locking
**How to avoid:** Use single UPDATE statement instead of read-modify-write, or accept slightly stale timestamps
**Warning signs:** Timestamps appear out of order in activity logs

### Pitfall 5: HTTPS Check at Wrong Layer
**What goes wrong:** Checking `request.url.scheme` returns `http` even for HTTPS traffic
**Why it happens:** Reverse proxy (Railway) terminates TLS, forwards as HTTP with `X-Forwarded-Proto` header
**How to avoid:** Check `X-Forwarded-Proto` header, or trust proxy to enforce HTTPS
**Warning signs:** All requests fail HTTPS check in production

### Pitfall 6: Rate Limit Key Collision
**What goes wrong:** Different API keys sharing same user get merged rate limit
**Why it happens:** Using `user:{user_id}` instead of `api_key:{key_id}` for rate limit key
**How to avoid:** Per CONTEXT.md - each key gets independent bucket, use `api_key:{key_id}`
**Warning signs:** One active key exhausts quota for user's other keys

## Code Examples

Verified patterns from official sources:

### Complete API Key Authentication Dependency
```python
# Source: FastAPI Security docs + project patterns
from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
import asyncio
import logging

from app.models import get_db, User, APIKey, SessionLocal
from app.services.api_key_service import compute_sha256_hash, verify_api_key as verify_argon2

logger = logging.getLogger(__name__)

api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="API key for programmatic access (obtain from Settings > API Keys)"
)

def _update_last_used(api_key_id: int):
    """Background task: update last_used_at timestamp."""
    from datetime import datetime, timezone
    db = SessionLocal()
    try:
        db.execute(
            "UPDATE api_keys SET last_used_at = :now WHERE id = :id",
            {"now": datetime.now(timezone.utc), "id": api_key_id}
        )
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_used_at for key {api_key_id}: {e}")
        db.rollback()
    finally:
        db.close()

async def get_current_user_from_api_key(
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: str | None = Depends(api_key_header),
    db: Session = Depends(get_db)
) -> User:
    """
    Authenticate user via API key for MCP/programmatic endpoints.

    - Rejects JWT authentication with helpful error
    - Returns specific error messages (expired, revoked) per requirements
    - Updates last_used_at asynchronously
    - Stores api_key_id in request.state for rate limiting
    """
    # Reject JWT if present
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires API key authentication. Use X-API-Key header instead of Bearer token."
        )

    # Require API key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Validate key format (optional but helpful)
    if not api_key.startswith("och_live_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format. Keys should start with 'och_live_'.",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Phase 1: Fast SHA-256 lookup
    sha256_hash = compute_sha256_hash(api_key)
    api_key_model = db.query(APIKey).filter(
        APIKey.key_hash_sha256 == sha256_hash
    ).first()

    if not api_key_model:
        logger.info(f"API key lookup failed: hash not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Check revocation (cheap check before expensive Argon2)
    if api_key_model.revoked_at is not None:
        logger.info(f"API key {api_key_model.id} rejected: revoked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Check expiration (cheap check before expensive Argon2)
    from datetime import datetime, timezone
    if api_key_model.expires_at is not None:
        if datetime.now(timezone.utc) >= api_key_model.expires_at:
            expiry_date = api_key_model.expires_at.strftime("%Y-%m-%d")
            logger.info(f"API key {api_key_model.id} rejected: expired on {expiry_date}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API key expired on {expiry_date}",
                headers={"WWW-Authenticate": "APIKey"}
            )

    # Phase 2: Argon2 verification (run in thread pool)
    is_valid = await asyncio.to_thread(
        verify_argon2, api_key, api_key_model.key_hash_argon2
    )

    if not is_valid:
        logger.warning(f"API key {api_key_model.id} failed Argon2 verification")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Load user
    user = db.query(User).filter(User.id == api_key_model.user_id).first()
    if not user:
        logger.error(f"API key {api_key_model.id} has orphaned user_id {api_key_model.user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key owner not found",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Store key ID for rate limiting
    request.state.api_key_id = api_key_model.id

    # Schedule async last_used update
    background_tasks.add_task(_update_last_used, api_key_model.id)

    logger.info(
        f"API key auth success: key_id={api_key_model.id} user_id={user.id} "
        f"key_name='{api_key_model.name}'"
    )

    return user
```

### Updated Rate Limiting Key Function
```python
# Source: Existing rate_limiting.py + per-key rate limit requirement
def get_rate_limit_key(request: Request) -> str:
    """
    Generate rate limit key based on authentication context.

    Priority:
    1. API key ID (each key gets independent 100 req/min bucket)
    2. Authenticated user ID (for JWT-authenticated requests)
    3. IP address (fallback for unauthenticated requests)
    """
    # Check for API key ID (set by get_current_user_from_api_key)
    if hasattr(request.state, "api_key_id") and request.state.api_key_id:
        return f"api_key:{request.state.api_key_id}"

    # Check for user ID (set by JWT auth)
    if hasattr(request.state, "user_id") and request.state.user_id:
        return f"user:{request.state.user_id}"

    # Fallback to IP address
    try:
        if hasattr(request, 'client') and hasattr(request.client, 'host'):
            return request.client.host
        return get_remote_address(request)
    except Exception as e:
        logger.warning(f"Failed to get remote address: {e}")
        return "unknown"
```

### MCP Auth Helper Update
```python
# Source: Existing backend/app/mcp/auth.py + API key pattern
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models import User, APIKey
from app.services.api_key_service import compute_sha256_hash, verify_api_key
import logging

logger = logging.getLogger(__name__)

def _extract_api_key_header(ctx: Any) -> Optional[str]:
    """Extract X-API-Key from various MCP context shapes."""
    # Try request_headers
    headers = getattr(ctx, "request_headers", None)
    if headers:
        key = headers.get("X-API-Key") or headers.get("x-api-key")
        if key:
            return key

    # Try headers
    headers = getattr(ctx, "headers", None)
    if headers:
        key = headers.get("X-API-Key") or headers.get("x-api-key")
        if key:
            return key

    # Try request.headers
    request = getattr(ctx, "request", None)
    if request:
        req_headers = getattr(request, "headers", None)
        if req_headers:
            key = req_headers.get("X-API-Key") or req_headers.get("x-api-key")
            if key:
                return key

    return None

def require_user_api_key(ctx: Any, db: Session) -> User:
    """
    Require authenticated user from API key for MCP context.

    This is the MCP equivalent of get_current_user_from_api_key dependency.
    Rejects JWT authentication - MCP endpoints are API key only.
    """
    # Check for JWT (reject it)
    bearer_token = extract_bearer_token(ctx)  # Existing function
    if bearer_token:
        raise PermissionError(
            "MCP endpoints require API key authentication. "
            "Use X-API-Key header instead of Bearer token."
        )

    # Extract API key
    api_key = _extract_api_key_header(ctx)
    if not api_key:
        raise PermissionError("Missing API key. Provide X-API-Key header.")

    # Validate format
    if not api_key.startswith("och_live_"):
        raise PermissionError("Invalid API key format.")

    # Phase 1: SHA-256 lookup
    sha256_hash = compute_sha256_hash(api_key)
    api_key_model = db.query(APIKey).filter(
        APIKey.key_hash_sha256 == sha256_hash
    ).first()

    if not api_key_model:
        raise PermissionError("Invalid API key")

    # Check revocation
    if api_key_model.revoked_at is not None:
        raise PermissionError("API key has been revoked")

    # Check expiration
    from datetime import datetime, timezone
    if api_key_model.expires_at is not None:
        if datetime.now(timezone.utc) >= api_key_model.expires_at:
            expiry_date = api_key_model.expires_at.strftime("%Y-%m-%d")
            raise PermissionError(f"API key expired on {expiry_date}")

    # Phase 2: Argon2 verification (sync for MCP context)
    is_valid = verify_api_key(api_key, api_key_model.key_hash_argon2)
    if not is_valid:
        raise PermissionError("Invalid API key")

    # Load user
    user = db.query(User).filter(User.id == api_key_model.user_id).first()
    if not user:
        raise PermissionError("API key owner not found")

    # Note: last_used_at update would need separate handling for MCP
    # Consider updating in finally block or accepting slight lag

    logger.info(f"MCP API key auth: key_id={api_key_model.id} user_id={user.id}")

    return user
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Middleware for auth | Dependency injection | FastAPI best practice | Better composability, testability |
| IP-only rate limiting | Per-credential rate limiting | Industry standard | Fair quotas per user/key |
| Generic "Invalid credentials" | Specific error messages | Modern API design | Better developer experience |
| Sync Argon2 in async context | asyncio.to_thread() | Python 3.9+ | Non-blocking verification |

**Deprecated/outdated:**
- **ASGI middleware for auth:** Use FastAPI dependencies instead (better DX, testing)
- **`compare_digest` on Python < 3.9:** Upgrade for CVE-2022-48566 fix
- **passlib for Argon2:** Use argon2-cffi directly (passlib unmaintained)

## Open Questions

Things that couldn't be fully resolved:

1. **MCP last_used_at update timing**
   - What we know: FastAPI BackgroundTasks work for HTTP endpoints
   - What's unclear: How to fire background tasks from sync MCP tool handlers
   - Recommendation: Accept slightly stale last_used_at for MCP (update on DB query completion) or use asyncio.create_task if MCP handler is async

2. **HTTPS enforcement location**
   - What we know: Railway terminates TLS before reaching app
   - What's unclear: Whether Railway enforces HTTPS or allows HTTP
   - Recommendation: Trust Railway's infrastructure to enforce HTTPS. Add `X-Forwarded-Proto` check if paranoid, but likely unnecessary.

3. **Rate limit bucket for revoked keys**
   - What we know: Revoked keys should fail auth immediately
   - What's unclear: Whether failed auth attempts should count against rate limit
   - Recommendation: Count against IP-based limit to prevent enumeration attacks, but auth failure happens before key ID is known anyway

## Sources

### Primary (HIGH confidence)
- [FastAPI Security Reference](https://fastapi.tiangolo.com/reference/security/) - APIKeyHeader documentation
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) - Official async task pattern
- Existing codebase: `/backend/app/auth/dependencies.py`, `/backend/app/core/rate_limiting.py`
- Phase 1 Research: `.planning/phases/01-database-model-&-core-logic/01-RESEARCH.md`

### Secondary (MEDIUM confidence)
- [GitHub - FastMCP Discussion #732](https://github.com/jlowin/fastmcp/discussions/732) - Middleware state propagation issues
- [Python hmac.compare_digest](https://docs.python.org/3/library/hmac.html) - Timing-safe comparison
- [slowapi GitHub](https://github.com/laurentS/slowapi) - Rate limiting patterns

### Tertiary (LOW confidence)
- WebSearch results on FastAPI API key patterns (2026) - Community patterns verified against official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in codebase or stdlib
- Architecture: HIGH - Patterns derived from existing auth/dependencies.py
- Pitfalls: HIGH - FastMCP state issue verified via GitHub discussion
- Code examples: HIGH - Based on existing codebase patterns and official docs

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - stable domain, FastAPI patterns well-established)
