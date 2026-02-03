"""
Service for creating and managing API keys.

Provides module-level functions for key generation and verification,
plus APIKeyService class for database operations.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlalchemy.orm import Session

from ..models import APIKey

logger = logging.getLogger(__name__)

# Module-level hasher (thread-safe, reusable)
_password_hasher = PasswordHasher()


def generate_api_key() -> Tuple[str, str, str, str]:
    """Generate a new API key with both hashes.

    Returns:
        tuple: (full_key, sha256_hash, argon2_hash, last_four)
            - full_key: The complete API key (och_live_ + 64 hex chars)
            - sha256_hash: SHA-256 hash for fast indexed lookup
            - argon2_hash: Argon2id hash for cryptographic verification
            - last_four: Last 4 characters for display purposes
    """
    random_part = secrets.token_hex(32)  # 256 bits of entropy
    full_key = f"och_live_{random_part}"

    sha256_hash = hashlib.sha256(full_key.encode('utf-8')).hexdigest()
    argon2_hash = _password_hasher.hash(full_key)
    last_four = random_part[-4:]

    return full_key, sha256_hash, argon2_hash, last_four


def verify_api_key(key: str, argon2_hash: str) -> bool:
    """Verify an API key against stored Argon2 hash.

    Args:
        key: The API key to verify
        argon2_hash: The stored Argon2id hash

    Returns:
        True if key matches, False otherwise
    """
    try:
        _password_hasher.verify(argon2_hash, key)
        return True
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def compute_sha256_hash(key: str) -> str:
    """Compute SHA-256 hash for fast lookup.

    Args:
        key: The API key to hash

    Returns:
        64-character hex SHA-256 hash
    """
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, db: Session):
        self.db = db

    def create_key(
        self,
        user_id: int,
        name: str,
        expires_at: Optional[datetime] = None
    ) -> Tuple[APIKey, str]:
        """Create a new API key for a user.

        Args:
            user_id: The user's ID
            name: Display name for the key
            expires_at: Optional expiration timestamp

        Returns:
            Tuple of (APIKey model, full_key_shown_once)

        Raises:
            ValueError: If name already exists for user
        """
        # Check for duplicate name
        existing = self.db.query(APIKey).filter(
            APIKey.user_id == user_id,
            APIKey.name == name,
            APIKey.revoked_at.is_(None)
        ).first()
        if existing:
            raise ValueError(f"API key with name '{name}' already exists")

        # Generate key and hashes
        full_key, sha256_hash, argon2_hash, last_four = generate_api_key()

        # Create model
        api_key = APIKey(
            user_id=user_id,
            name=name,
            key_hash_sha256=sha256_hash,
            key_hash_argon2=argon2_hash,
            last_four=last_four,
            expires_at=expires_at
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        logger.info(
            "Created API key '%s' (id=%d) for user_id=%d",
            name, api_key.id, user_id
        )

        return api_key, full_key

    def list_user_keys(self, user_id: int, include_revoked: bool = False) -> List[APIKey]:
        """List all API keys for a user.

        Args:
            user_id: The user's ID
            include_revoked: Whether to include revoked keys

        Returns:
            List of APIKey models, ordered by creation date descending
        """
        query = self.db.query(APIKey).filter(APIKey.user_id == user_id)
        if not include_revoked:
            query = query.filter(APIKey.revoked_at.is_(None))
        return query.order_by(APIKey.created_at.desc()).all()

    def revoke_key(self, key_id: int, user_id: int) -> bool:
        """Revoke an API key (hard delete).

        Args:
            key_id: The API key ID
            user_id: The user's ID (for ownership verification)

        Returns:
            True if key was deleted, False if not found
        """
        api_key = self.db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id,
            APIKey.revoked_at.is_(None)
        ).first()

        if not api_key:
            return False

        key_name = api_key.name
        self.db.delete(api_key)
        self.db.commit()

        logger.info(
            "Deleted API key '%s' (id=%d) for user_id=%d",
            key_name, key_id, user_id
        )

        return True

    def find_by_sha256_hash(self, sha256_hash: str) -> Optional[APIKey]:
        """Find API key by SHA-256 hash for fast lookup.

        Args:
            sha256_hash: The SHA-256 hash of the API key

        Returns:
            APIKey if found and not revoked, None otherwise
        """
        return self.db.query(APIKey).filter(
            APIKey.key_hash_sha256 == sha256_hash,
            APIKey.revoked_at.is_(None)
        ).first()

    def update_last_used(self, api_key: APIKey) -> None:
        """Update the last_used_at timestamp for an API key.

        Args:
            api_key: The APIKey model to update
        """
        api_key.last_used_at = datetime.now(timezone.utc)
        self.db.commit()
