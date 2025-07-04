"""
OAuth provider model for linking multiple authentication providers to users.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import Base

class OAuthProvider(Base):
    __tablename__ = "oauth_providers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)  # 'google', 'github'
    provider_user_id = Column(String(255), nullable=False)  # OAuth provider's user ID
    access_token = Column(Text, nullable=True)  # Encrypted access token
    refresh_token = Column(Text, nullable=True)  # Encrypted refresh token
    token_expires_at = Column(DateTime(timezone=True), nullable=True)
    is_primary = Column(Boolean, default=False)  # Primary login method
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="oauth_providers")
    
    def __repr__(self):
        return f"<OAuthProvider(user_id={self.user_id}, provider='{self.provider}', primary={self.is_primary})>"

class UserEmail(Base):
    __tablename__ = "user_emails"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    is_primary = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    source = Column(String(50), nullable=True)  # 'google', 'github', 'manual'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="emails")
    
    def __repr__(self):
        return f"<UserEmail(user_id={self.user_id}, email='{self.email}', primary={self.is_primary})>"