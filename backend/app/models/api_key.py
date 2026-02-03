"""
API Key model for programmatic access to On-Call Health.

Uses dual-hash storage pattern:
- SHA-256 for fast indexed lookup
- Argon2id for cryptographic verification
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base


class APIKey(Base):
    """
    API Key model for programmatic access.

    Storage pattern:
    - key_hash_sha256: Fast indexed lookup (64 hex chars)
    - key_hash_argon2: Cryptographic verification (timing-safe)

    Key format: {prefix}{random_hex} (e.g., och_live_a1b2c3d4...)
    """
    __tablename__ = "api_keys"

    # Primary key (Integer to match codebase pattern)
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to user
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # Key metadata
    name = Column(String(255), nullable=False)

    # Dual-hash storage (never store plaintext)
    key_hash_sha256 = Column(String(64), nullable=False)  # Fast indexed lookup
    key_hash_argon2 = Column(Text, nullable=False)  # Cryptographic verification

    # Key display fields (safe to show)
    prefix = Column(String(20), nullable=False, default="och_live_")
    last_four = Column(String(4), nullable=False)

    # Scope (v1: full_access only)
    scope = Column(String(50), nullable=False, default="full_access")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Table constraints and indexes
    __table_args__ = (
        UniqueConstraint('user_id', 'name', name='uq_api_keys_user_name'),
        Index('idx_api_keys_key_hash_sha256', 'key_hash_sha256'),
        Index('idx_api_keys_user_id', 'user_id'),
        Index('idx_api_keys_last_used_at', 'last_used_at'),
    )

    # Relationships
    user = relationship("User", back_populates="api_keys")

    @property
    def is_active(self) -> bool:
        """
        Check if key is active (not revoked and not expired).

        Returns:
            True if key can be used for authentication.
        """
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None:
            return datetime.now(timezone.utc) < self.expires_at
        return True

    @property
    def masked_key(self) -> str:
        """
        Get masked representation of key for display.

        Returns:
            String in format "{prefix}...{last_four}" (e.g., "och_live_...abcd")
        """
        return f"{self.prefix}...{self.last_four}"

    def to_dict(self, include_sensitive: bool = False) -> dict:
        """
        Convert model to dictionary for API responses.

        Args:
            include_sensitive: If True, include internal fields (for admin views)

        Returns:
            Dictionary representation of the API key.
        """
        data = {
            'id': self.id,
            'name': self.name,
            'masked_key': self.masked_key,
            'scope': self.scope,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() if self.last_used_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revoked_at': self.revoked_at.isoformat() if self.revoked_at else None,
        }

        if include_sensitive:
            data['user_id'] = self.user_id
            data['prefix'] = self.prefix
            data['last_four'] = self.last_four

        return data

    def __repr__(self) -> str:
        return (
            f"<APIKey(id={self.id}, name='{self.name}', "
            f"user_id={self.user_id}, is_active={self.is_active})>"
        )
