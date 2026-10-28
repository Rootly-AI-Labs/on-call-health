"""Encryption helpers for tokens stored in the database."""
import base64
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from .config import settings

FERNET_TOKEN_PREFIX = "gAAAAA"


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


class EncryptedText(TypeDecorator):
    """Text column encrypted at rest. Values written before encryption are read as stored."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return encrypt_optional_token(value)

    def process_result_value(self, value, dialect):
        if value is None or not value.startswith(FERNET_TOKEN_PREFIX):
            return value
        try:
            return decrypt_token(value)
        except InvalidToken:
            return value
