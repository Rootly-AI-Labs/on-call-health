"""
API key authentication dependency for FastAPI.

Provides get_current_user_from_api_key for programmatic API endpoints.
Uses two-phase validation: SHA-256 lookup (fast) + Argon2 verification (secure).
"""
import asyncio
import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..models import get_db, User, APIKey, SessionLocal
from ..services.api_key_service import compute_sha256_hash, verify_api_key

logger = logging.getLogger(__name__)

# API key header scheme - X-API-Key is the conventional header name
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,  # We'll handle errors ourselves for better messages
    description="API key for programmatic access"
)


def _update_last_used_background(api_key_id: int) -> None:
    """Background task to update last_used_at timestamp.

    Creates a new session for thread safety (BackgroundTasks run after response).
    Uses raw SQL UPDATE for efficiency.

    Args:
        api_key_id: The ID of the API key to update
    """
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE api_keys SET last_used_at = :now WHERE id = :id"),
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
    Authenticate user via API key for programmatic endpoints.

    Two-phase validation:
    1. SHA-256 lookup (fast, indexed) - finds the key record
    2. Argon2 verification (timing-safe) - confirms key is correct

    Error messages are specific per requirements:
    - Revoked keys: "API key has been revoked" (no date)
    - Expired keys: "API key expired on YYYY-MM-DD" (with date)

    Args:
        request: FastAPI request object
        background_tasks: FastAPI background tasks for async last_used update
        api_key: API key from X-API-Key header
        db: Database session

    Returns:
        User: The authenticated user

    Raises:
        HTTPException: 400 if JWT token provided (wrong auth method)
        HTTPException: 401 if API key invalid, revoked, expired, or owner not found
    """
    # Check for JWT in Authorization header - reject with helpful error
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and not auth_header.startswith("Bearer och_live_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint requires API key authentication. Use X-API-Key header instead of Bearer token."
        )

    # Require API key
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "APIKey"}
        )

    # Validate key format
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
        logger.info("API key lookup failed: hash not found")
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
    if api_key_model.expires_at is not None:
        if datetime.now(timezone.utc) >= api_key_model.expires_at:
            expiry_date = api_key_model.expires_at.strftime("%Y-%m-%d")
            logger.info(f"API key {api_key_model.id} rejected: expired on {expiry_date}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"API key expired on {expiry_date}",
                headers={"WWW-Authenticate": "APIKey"}
            )

    # Phase 2: Argon2 verification (run in thread pool to avoid blocking)
    is_valid = await asyncio.to_thread(
        verify_api_key, api_key, api_key_model.key_hash_argon2
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

    # Store key ID in request state for rate limiting
    request.state.api_key_id = api_key_model.id

    # Schedule async last_used update (fire and forget)
    background_tasks.add_task(_update_last_used_background, api_key_model.id)

    logger.info(
        f"API key auth success: key_id={api_key_model.id} user_id={user.id} "
        f"key_name='{api_key_model.name}'"
    )

    return user
