"""Encryption helpers for tokens stored in the database."""
import base64
from typing import Optional

from cryptography.fernet import Fernet

from .config import settings


def get_encryption_key() -> bytes:
    key = settings.JWT_SECRET_KEY.encode()
    return base64.urlsafe_b64encode(key[:32].ljust(32, b"\0"))


def encrypt_token(token: str) -> str:
    return Fernet(get_encryption_key()).encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    return Fernet(get_encryption_key()).decrypt(encrypted_token.encode()).decode()


def encrypt_optional_token(token: Optional[str]) -> Optional[str]:
    if token is None:
        return None
    return encrypt_token(token)
