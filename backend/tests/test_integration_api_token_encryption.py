import os
import sys

from sqlalchemy import Column, Integer, MetaData, Table, create_engine, select, text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.token_encryption import EncryptedText, decrypt_token, encrypt_token
from app.models import RootlyIntegration

API_TOKEN = "rootly_test-api-token"


def _table_with_encrypted_column():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    table = Table(
        "integrations",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("api_token", EncryptedText()),
    )
    metadata.create_all(engine)
    return engine, table


def _raw_value(conn):
    return conn.execute(text("SELECT api_token FROM integrations")).scalar_one()


def test_rootly_integration_api_token_is_encrypted_column():
    assert isinstance(RootlyIntegration.__table__.c.api_token.type, EncryptedText)


def test_written_token_is_stored_encrypted_and_read_back_plain():
    engine, table = _table_with_encrypted_column()
    with engine.begin() as conn:
        conn.execute(table.insert().values(id=1, api_token=API_TOKEN))

        stored = _raw_value(conn)
        assert stored != API_TOKEN
        assert decrypt_token(stored) == API_TOKEN
        assert conn.execute(select(table.c.api_token)).scalar_one() == API_TOKEN


def test_legacy_plaintext_token_is_read_unchanged():
    engine, table = _table_with_encrypted_column()
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO integrations (id, api_token) VALUES (1, :token)"), {"token": API_TOKEN})

        assert conn.execute(select(table.c.api_token)).scalar_one() == API_TOKEN


def test_already_encrypted_value_is_not_encrypted_twice():
    engine, table = _table_with_encrypted_column()
    with engine.begin() as conn:
        conn.execute(table.insert().values(id=1, api_token=encrypt_token(API_TOKEN)))

        assert decrypt_token(_raw_value(conn)) == API_TOKEN


def test_null_token_stays_null():
    engine, table = _table_with_encrypted_column()
    with engine.begin() as conn:
        conn.execute(table.insert().values(id=1, api_token=None))

        assert _raw_value(conn) is None
        assert conn.execute(select(table.c.api_token)).scalar_one() is None
