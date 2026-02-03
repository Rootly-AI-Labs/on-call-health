"""
API key management endpoints.

Provides CRUD operations for API keys used by the web UI.
All endpoints require JWT authentication (not API keys) to prevent
compromised key escalation.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, Field, field_validator

from ...models import get_db, User
from ...auth.dependencies import get_current_active_user
from ...services.api_key_service import APIKeyService
from ...core.rate_limiting import integration_rate_limit


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


router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"]
)


@router.post("", status_code=status.HTTP_201_CREATED)
@integration_rate_limit("integration_create")
async def create_api_key(
    request: Request,
    body: CreateApiKeyRequest,
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
            name=body.name,
            expires_at=body.expires_at
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"An API key named '{body.name}' already exists. Please choose a different name."
        )

    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": full_key,
        "masked_key": api_key.masked_key,
        "scope": api_key.scope,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None
    }


@router.get("")
@integration_rate_limit("integration_get")
async def list_api_keys(
    request: Request,
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


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
@integration_rate_limit("integration_update")
async def revoke_api_key(
    request: Request,
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
