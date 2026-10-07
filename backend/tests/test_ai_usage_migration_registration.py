"""Tracked AI usage migrations in a rollback-only disposable database.

The imported fixtures require a retention_test PostgreSQL target. Each database
case uses an isolated schema so it cannot alter application or other test tables.
"""
from uuid import uuid4

import pytest
from sqlalchemy import text

from .test_retention_preview import db, db_connection, retention_engine


CREATE_NAME = "056_create_ai_usage_integrations"
ALTER_NAME = "053_ai_usage_nullable_org"


def registered_migrations():
    from migrations.migration_runner import MigrationRunner

    runner = MigrationRunner.__new__(MigrationRunner)
    registered = []

    def capture(name, commands):
        registered.append((name, commands))
        return True

    runner.run_sql_migration = capture
    assert runner.run_all_migrations()
    return registered


def test_ai_usage_creation_is_registered_before_existing_alteration():
    registered = registered_migrations()
    names = [name for name, _ in registered]
    assert names.count(CREATE_NAME) == names.count(ALTER_NAME) == 1
    assert names.index(CREATE_NAME) < names.index(ALTER_NAME)
    # Existing tracked names must remain intact across upgrades.
    assert "052_add_openai_user_id_to_user_correlations" in names
    assert "054_add_pagerduty_teams_to_user_correlations" in names
    assert "055_add_analysis_results_generated_at" in names
    creation = dict(registered)[CREATE_NAME]
    assert any("CREATE TABLE IF NOT EXISTS ai_usage_integrations" in sql for sql in creation)


@pytest.fixture
def isolated_runner(db, db_connection):
    from migrations.migration_runner import MigrationRunner

    schema = f"ai_usage_migration_{uuid4().hex}"
    db_connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    db_connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
    db.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
    db.execute(text("CREATE TABLE organizations (id INTEGER PRIMARY KEY)"))
    db.execute(text("INSERT INTO users (id) VALUES (1), (2), (3)"))
    db.execute(text("INSERT INTO organizations (id) VALUES (10)"))
    db.commit()
    runner = MigrationRunner.__new__(MigrationRunner)
    runner.db = db
    runner.ensure_migrations_table()
    return runner, schema


def org_nullable(db, schema):
    return db.execute(text(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_schema = :schema AND table_name = 'ai_usage_integrations' "
        "AND column_name = 'organization_id'"
    ), {"schema": schema}).scalar_one()


def test_tracked_creation_and_alteration_work_without_orm_create_all(db, isolated_runner):
    from sqlalchemy.exc import IntegrityError

    runner, schema = isolated_runner
    registered = dict(registered_migrations())
    assert runner.run_sql_migration(CREATE_NAME, registered[CREATE_NAME])
    assert org_nullable(db, schema) == "NO"
    assert runner.run_sql_migration(ALTER_NAME, registered[ALTER_NAME])
    assert org_nullable(db, schema) == "YES"

    db.execute(text(
        "INSERT INTO ai_usage_integrations (user_id, organization_id) "
        "VALUES (1, NULL), (2, NULL), (3, 10)"
    ))
    db.commit()
    # Keep one personal integration per owner and one shared row per org.
    for user_id, org_id in [(1, None), (2, 10)]:
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(text(
                "INSERT INTO ai_usage_integrations (user_id, organization_id) "
                "VALUES (:user_id, :org_id)"
            ), {"user_id": user_id, "org_id": org_id})
    assert db.execute(text("SELECT count(*) FROM ai_usage_integrations")).scalar_one() == 3

    for name in [CREATE_NAME, ALTER_NAME]:
        assert runner.is_migration_applied(name)
        assert runner.run_sql_migration(name, registered[name])
    assert org_nullable(db, schema) == "YES"


def test_missing_creation_tracking_preserves_existing_nullable_table_and_rows(db, isolated_runner):
    runner, schema = isolated_runner
    registered = dict(registered_migrations())
    # Model an installation where ORM setup created the table and 053 already ran.
    for command in registered[CREATE_NAME] + registered[ALTER_NAME]:
        db.execute(text(command))
    db.execute(text(
        "INSERT INTO ai_usage_integrations (user_id, organization_id, openai_org_id) "
        "VALUES (1, NULL, 'disposable-existing-org')"
    ))
    db.commit()
    runner.mark_migration_applied(ALTER_NAME)
    assert not runner.is_migration_applied(CREATE_NAME)

    assert runner.run_sql_migration(CREATE_NAME, registered[CREATE_NAME])
    assert runner.run_sql_migration(ALTER_NAME, registered[ALTER_NAME])
    assert org_nullable(db, schema) == "YES"
    assert db.execute(text(
        "SELECT user_id, organization_id, openai_org_id FROM ai_usage_integrations"
    )).all() == [(1, None, "disposable-existing-org")]
    assert runner.is_migration_applied(CREATE_NAME)
