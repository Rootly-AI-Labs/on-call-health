# Phase 3: API Endpoints - Research

**Researched:** 2026-01-30
**Domain:** FastAPI REST API Endpoints for API Key Management (CRUD)
**Confidence:** HIGH

## Summary

This research investigated how to implement REST API endpoints for API key management (create, list, revoke) in the existing FastAPI codebase. The phase focuses on endpoints exclusively for the web UI that require JWT authentication - programmatic API key management is deliberately excluded for security (prevents compromised key escalation).

The existing codebase has well-established patterns in `/backend/app/api/endpoints/` (e.g., `invitations.py`, `admin.py`) using Pydantic models for request/response validation, FastAPI dependencies for authentication (`get_current_active_user`), and inline dictionary responses with `Dict[str, Any]` type hints. The API key service layer (`/backend/app/services/api_key_service.py`) already provides all CRUD operations needed.

The CONTEXT.md decisions specify: flat JSON responses for single operations, wrapped responses for lists (`{"keys": [...]}`), simple error format (`{"error": "..."}`), and standard HTTP status codes (201, 200, 204, 400, 404).

**Primary recommendation:** Create `/backend/app/api/endpoints/api_keys.py` following existing endpoint patterns. Use Pydantic models for request validation (extending `BaseValidatedModel`), leverage the existing `APIKeyService` class, and apply JWT-only authentication via `get_current_active_user` dependency.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | Route definitions, dependency injection | Already in use throughout codebase |
| Pydantic v2 | existing | Request/response validation | Already used in `input_validation.py` |
| SQLAlchemy | existing | Database operations | Existing ORM pattern in codebase |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| slowapi | existing | Rate limiting | Per RATE_LIMITS config for API endpoints |
| BaseValidatedModel | existing | Input sanitization | All request schemas (from `input_validation.py`) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Inline dict responses | Response models | Codebase uses inline dicts; consistency > formality |
| Service class | Raw SQLAlchemy | Service exists with all CRUD methods - use it |
| Custom validation | Pydantic validators | BaseValidatedModel handles sanitization already |

**Installation:**
No new dependencies needed - all libraries already in use.

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       └── api_keys.py      # NEW: API key CRUD endpoints
│   ├── services/
│   │   └── api_key_service.py   # EXISTING: Business logic
│   └── models/
│       └── api_key.py           # EXISTING: SQLAlchemy model
└── tests/
    └── test_api_keys_endpoints.py  # NEW: Endpoint tests
```

### Pattern 1: JWT-Only Authentication (Matches CONTEXT.md Decision)
**What:** All API key management endpoints require JWT authentication, explicitly reject API keys
**When to use:** All endpoints in this phase (create, list, revoke)
**Why:** UI-only management prevents compromised key from creating more keys

**Example:**
```python
# Source: Existing backend/app/api/endpoints/invitations.py pattern
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from ...models import get_db, User
from ...auth.dependencies import get_current_active_user

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"]
)

@router.post("")
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_active_user),  # JWT only
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new API key for the current user."""
    # ...
```

### Pattern 2: Flat JSON Response (Matches CONTEXT.md Decision)
**What:** Single-resource operations return flat JSON without wrapper
**When to use:** Create, revoke endpoints
**Why:** Per CONTEXT.md: `{"id": "123", "name": "Claude Desktop", ...}`

**Example:**
```python
# Source: CONTEXT.md decision - flat JSON for single operations
@router.post("", status_code=201)
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new API key. Returns the full key ONCE."""
    service = APIKeyService(db)

    try:
        api_key, full_key = service.create_key(
            user_id=current_user.id,
            name=request.name,
            expires_at=request.expires_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Return flat JSON with full key shown once
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,  # Shown ONCE - REQ-F-003
        "masked_key": api_key.masked_key,
        "scope": api_key.scope,
        "created_at": api_key.created_at.isoformat(),
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None
    }
```

### Pattern 3: Wrapped List Response (Matches CONTEXT.md Decision)
**What:** List operations return wrapped JSON with object containing array
**When to use:** List endpoint
**Why:** Per CONTEXT.md: `{"keys": [{...}, {...}]}` - allows adding pagination metadata later

**Example:**
```python
# Source: CONTEXT.md decision - list wrapped in object
@router.get("")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List all API keys for the current user."""
    service = APIKeyService(db)
    keys = service.list_user_keys(user_id=current_user.id, include_revoked=False)

    # Wrapped response per CONTEXT.md
    return {
        "keys": [
            {
                "id": key.id,
                "name": key.name,
                "masked_key": key.masked_key,  # REQ-F-010
                "scope": key.scope,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat(),
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None
            }
            for key in keys
        ]
    }
```

### Pattern 4: Simple Error Format (Matches CONTEXT.md Decision)
**What:** Errors return minimal JSON with error message
**When to use:** All error responses
**Why:** Per CONTEXT.md: `{"error": "Invalid API key name"}`

**Example:**
```python
# Source: CONTEXT.md decision - simple error format
# Note: FastAPI HTTPException already produces {"detail": "..."} format
# For consistency with CONTEXT.md, we can customize this:

@router.post("", status_code=201)
async def create_api_key(...) -> Dict[str, Any]:
    if not request.name or len(request.name.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="API key name is required"  # Maps to {"detail": "..."}
        )

    try:
        api_key, full_key = service.create_key(...)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

Note: FastAPI uses `detail` by default. To use `error` as per CONTEXT.md, a custom exception handler would be needed. Given existing codebase uses `detail`, recommend staying consistent unless specifically requested to change.

### Pattern 5: Soft Delete for Revocation (Matches Existing APIKeyService)
**What:** Revoke sets `revoked_at` timestamp instead of deleting
**When to use:** DELETE /api-keys/{key_id}
**Why:** Audit trail, prevents reuse of revoked key IDs

**Example:**
```python
# Source: Existing api_key_service.py revoke_key method
@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> None:
    """Revoke (soft-delete) an API key."""
    service = APIKeyService(db)

    if not service.revoke_key(key_id=key_id, user_id=current_user.id):
        raise HTTPException(
            status_code=404,
            detail="API key not found or already revoked"
        )

    # 204 No Content - no response body per CONTEXT.md
    return None
```

### Anti-Patterns to Avoid
- **Accepting API keys for key management:** Never use `get_current_user_from_api_key` - UI-only per security decision
- **Exposing full key after creation:** Only show once in create response, never in list
- **Hard-deleting keys:** Use soft delete (revoked_at) for audit trail
- **Complex nested responses:** Keep flat per CONTEXT.md decisions
- **Custom error formats different from codebase:** Use existing `detail` pattern

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Key generation | Custom random + hash | `APIKeyService.create_key()` | Handles dual-hash pattern |
| Key revocation | Manual SQL update | `APIKeyService.revoke_key()` | Handles ownership check |
| Key listing | Raw query with filters | `APIKeyService.list_user_keys()` | Handles ordering, filtering |
| Input sanitization | Custom validators | `BaseValidatedModel` | XSS, injection protection built-in |
| Authentication | Custom JWT parsing | `get_current_active_user` | Handles cookies + headers |

**Key insight:** The `APIKeyService` class from Phase 1 provides all business logic. The endpoints are thin wrappers that handle HTTP concerns only.

## Common Pitfalls

### Pitfall 1: Returning Full Key in List Response
**What goes wrong:** Full API key exposed on list, creating security risk
**Why it happens:** Copy-paste from create response, forgetting security model
**How to avoid:** Always use `masked_key` property for list/get, only return full key on create
**Warning signs:** `key` field in list response, storing full key anywhere client-side

### Pitfall 2: Not Validating Ownership on Revoke
**What goes wrong:** User can revoke another user's keys
**Why it happens:** Forgetting to pass `user_id` to `revoke_key()`
**How to avoid:** Always pass `user_id=current_user.id` to service methods
**Warning signs:** Missing `user_id` parameter in service calls

### Pitfall 3: Using Wrong Authentication Dependency
**What goes wrong:** API keys can be used to create/manage other API keys
**Why it happens:** Using `get_current_user_from_api_key` instead of `get_current_active_user`
**How to avoid:** Only import and use `get_current_active_user` in api_keys.py
**Warning signs:** `api_key_auth` imports in the endpoints file

### Pitfall 4: Forgetting Rate Limiting
**What goes wrong:** Key creation endpoint abused for enumeration
**Why it happens:** Not adding rate limiting decorator
**How to avoid:** Add `@integration_rate_limit("integration_create")` to create endpoint
**Warning signs:** No rate limit decorators on mutation endpoints

### Pitfall 5: Duplicate Key Name Not Handled Gracefully
**What goes wrong:** Internal ValueError leaks to user
**Why it happens:** Not catching `ValueError` from `service.create_key()`
**How to avoid:** Catch `ValueError` and return HTTP 400 with message
**Warning signs:** 500 errors on duplicate name submission

### Pitfall 6: Missing Expiration Date Validation
**What goes wrong:** User can create keys that expire in the past
**Why it happens:** Not validating `expires_at` is in the future
**How to avoid:** Add Pydantic validator or check in endpoint
**Warning signs:** Keys created with past expiration dates

## Code Examples

Verified patterns from official sources:

### Complete Create Endpoint
```python
# Source: Existing invitations.py pattern + api_key_service.py
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models import get_db, User
from ...auth.dependencies import get_current_active_user
from ...services.api_key_service import APIKeyService
from ...core.rate_limiting import integration_rate_limit

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class CreateApiKeyRequest(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name for the API key"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration date (must be in future)"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate name is not just whitespace."""
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty or whitespace")
        return v

    @field_validator('expires_at')
    @classmethod
    def validate_expires_at(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Validate expiration is in the future."""
        if v is not None:
            # Ensure timezone-aware
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v <= datetime.now(timezone.utc):
                raise ValueError("Expiration date must be in the future")
        return v


@router.post("", status_code=status.HTTP_201_CREATED)
@integration_rate_limit("integration_create")
async def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create a new API key for the current user.

    The full key is returned ONLY in this response.
    Store it securely - it cannot be retrieved again.
    """
    service = APIKeyService(db)

    try:
        api_key, full_key = service.create_key(
            user_id=current_user.id,
            name=request.name,
            expires_at=request.expires_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,  # Shown once only
        "masked_key": api_key.masked_key,
        "scope": api_key.scope,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None
    }
```

### Complete List Endpoint
```python
# Source: Existing invitations.py list_pending_invitations pattern
@router.get("")
@integration_rate_limit("integration_get")
async def list_api_keys(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all active API keys for the current user.

    Returns masked keys only - full keys are never exposed after creation.
    """
    service = APIKeyService(db)
    keys = service.list_user_keys(user_id=current_user.id, include_revoked=False)

    return {
        "keys": [
            {
                "id": key.id,
                "name": key.name,
                "masked_key": key.masked_key,
                "scope": key.scope,
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used_at": key.last_used_at.isoformat() if key.last_used_at else None,
                "expires_at": key.expires_at.isoformat() if key.expires_at else None
            }
            for key in keys
        ]
    }
```

### Complete Revoke Endpoint
```python
# Source: Existing invitations.py revoke_invitation pattern
from fastapi import Response

@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@integration_rate_limit("integration_update")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Response:
    """
    Revoke an API key.

    This is a soft delete - the key is marked as revoked but not removed.
    Revoked keys cannot be used for authentication.
    """
    service = APIKeyService(db)

    if not service.revoke_key(key_id=key_id, user_id=current_user.id):
        raise HTTPException(
            status_code=404,
            detail="API key not found or already revoked"
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

### Router Registration
```python
# Source: Existing backend/app/api/__init__.py pattern
# In backend/app/api/endpoints/__init__.py or main router file:
from .api_keys import router as api_keys_router

# In main app setup:
app.include_router(
    api_keys_router,
    prefix="/api/v1",
    tags=["api-keys"]
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 validators | Pydantic v2 `field_validator` | 2024 | Use `@field_validator` decorator |
| `response_model=` for all | Return `Dict[str, Any]` | Codebase pattern | Simpler, matches existing code |
| UUID primary keys | Integer PKs | Prior decision | Match codebase pattern |

**Deprecated/outdated:**
- **Pydantic v1 `@validator`:** Use v2 `@field_validator` with `@classmethod`
- **`response_model_exclude_unset`:** Not needed with inline dict construction
- **Generic "Invalid request":** Per CONTEXT.md discretion, use specific error messages

## Open Questions

Things that couldn't be fully resolved:

1. **Exact rate limit values for API key endpoints**
   - What we know: CONTEXT.md says "Claude's discretion"
   - What's unclear: Optimal values for create/list/revoke
   - Recommendation: Use existing `integration_create` (5/min) for create, `integration_get` (200/min) for list, `integration_update` (10/min) for revoke

2. **Sort order for list endpoint**
   - What we know: CONTEXT.md says "Claude's discretion"
   - What's unclear: User preference (newest first vs alphabetical)
   - Recommendation: Use existing service behavior (created_at DESC) - newest first

3. **Handling duplicate key names**
   - What we know: Service raises `ValueError` on duplicate
   - What's unclear: Should we allow duplicate names for revoked keys?
   - Recommendation: Current service allows duplicate if prior key revoked - keep this behavior

4. **Error format: `detail` vs `error`**
   - What we know: CONTEXT.md says `{"error": "..."}`, codebase uses `{"detail": "..."}`
   - What's unclear: Whether to add custom exception handler
   - Recommendation: Use existing `detail` pattern for consistency with codebase

## Sources

### Primary (HIGH confidence)
- Existing codebase: `/backend/app/api/endpoints/invitations.py` - endpoint patterns
- Existing codebase: `/backend/app/services/api_key_service.py` - CRUD operations
- Existing codebase: `/backend/app/auth/dependencies.py` - JWT auth pattern
- Existing codebase: `/backend/app/core/input_validation.py` - Pydantic v2 patterns
- Phase 1 CONTEXT.md decisions - response formats and status codes

### Secondary (MEDIUM confidence)
- [FastAPI Best Practices](https://github.com/zhanymkanov/fastapi-best-practices) - Route organization, service layer
- [FastAPI Response Model docs](https://fastapi.tiangolo.com/tutorial/response-model/) - Response validation
- [Pydantic v2 Models](https://docs.pydantic.dev/latest/concepts/models/) - Validation patterns

### Tertiary (LOW confidence)
- WebSearch results on FastAPI API key management patterns - verified against official docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in codebase
- Architecture: HIGH - Patterns derived from existing endpoints (invitations.py)
- Code examples: HIGH - Based on existing codebase patterns
- Pitfalls: HIGH - Based on common issues in similar implementations

**Research date:** 2026-01-30
**Valid until:** 2026-03-01 (30 days - stable domain, patterns well-established)
