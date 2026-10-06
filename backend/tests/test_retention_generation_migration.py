"""Exercise the actual startup migration loader in disposable PostgreSQL only."""
from .test_retention_preview import (
    NOW, OLD, RECENT, analysis_factory, coverage, db, db_connection,
    organizations, retention_engine, users,
)


def test_generation_migration_backfills_only_known_successful_snapshots(db, analysis_factory):
    from sqlalchemy import text
    from migrations.migration_runner import MigrationRunner

    successful = analysis_factory(coverage(RECENT), results_generated_at=None, completed_at=OLD)
    failed = analysis_factory(coverage(RECENT), results_generated_at=None, status="failed", completed_at=NOW)
    unknown = analysis_factory(coverage(RECENT), results_generated_at=None, completed_at=None)
    canonical = analysis_factory(coverage(OLD), results_generated_at=RECENT, completed_at=OLD)
    original_payloads = [row.results for row in (successful, failed, unknown, canonical)]

    # The startup runner splits SQL files. Test that path rather than submitting
    # the whole file as one statement, so quoted-comment parsing issues surface.
    runner = MigrationRunner.__new__(MigrationRunner)
    commands = runner.load_sql_file("2026_10_05_add_analysis_results_generated_at.sql")
    assert len(commands) == 3
    for _ in range(2):
        for command in commands:
            db.execute(text(command))
        db.commit()
        for row in (successful, failed, unknown, canonical):
            db.refresh(row)
        assert successful.results_generated_at == OLD
        assert failed.results_generated_at is None
        assert unknown.results_generated_at is None
        assert canonical.results_generated_at == RECENT
        assert [row.results for row in (successful, failed, unknown, canonical)] == original_payloads
