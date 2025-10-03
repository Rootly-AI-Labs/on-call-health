#!/usr/bin/env python3
"""
Migration Runner for Rootly Burnout Detector

This system automatically manages database migrations in order.
Each migration is tracked in a migrations table to avoid re-running.
"""

import sys
import os
import logging
from datetime import datetime
from typing import List, Dict

# Add the correct paths for Docker environment
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
app_dir = os.path.join(backend_dir, 'app')

# Add both backend and app directories to Python path
sys.path.insert(0, backend_dir)
sys.path.insert(0, app_dir)

try:
    from app.models import get_db
    from sqlalchemy import text, create_engine
    from sqlalchemy.exc import SQLAlchemyError
except ImportError as e:
    # Fallback for Docker environment
    sys.path.insert(0, '/app')
    sys.path.insert(0, '/app/app')
    from app.models import get_db
    from sqlalchemy import text, create_engine
    from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self):
        self.db = next(get_db())
        self.ensure_migrations_table()

    def ensure_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        try:
            self.db.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'completed'
                )
            """))
            self.db.commit()
            logger.info("✅ Migrations table ready")
        except Exception as e:
            logger.error(f"❌ Failed to create migrations table: {e}")
            raise

    def is_migration_applied(self, migration_name: str) -> bool:
        """Check if a migration has already been applied"""
        try:
            result = self.db.execute(text("""
                SELECT COUNT(*) as count FROM migrations
                WHERE name = :name AND status = 'completed'
            """), {"name": migration_name})
            count = result.fetchone()[0]
            return count > 0
        except Exception:
            return False

    def mark_migration_applied(self, migration_name: str):
        """Mark a migration as applied"""
        try:
            self.db.execute(text("""
                INSERT INTO migrations (name, status)
                VALUES (:name, 'completed')
                ON CONFLICT (name) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    status = 'completed'
            """), {"name": migration_name})
            self.db.commit()
            logger.info(f"✅ Marked migration as applied: {migration_name}")
        except Exception as e:
            logger.error(f"❌ Failed to mark migration as applied: {e}")

    def run_sql_migration(self, migration_name: str, sql_commands: List[str]) -> bool:
        """Run a SQL-based migration"""
        if self.is_migration_applied(migration_name):
            logger.info(f"⏭️  Skipping already applied migration: {migration_name}")
            return True

        logger.info(f"🔧 Running migration: {migration_name}")

        try:
            for sql in sql_commands:
                self.db.execute(text(sql))

            self.db.commit()
            self.mark_migration_applied(migration_name)
            logger.info(f"✅ Successfully applied migration: {migration_name}")
            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {migration_name} - {e}")
            self.db.rollback()
            return False

    def run_all_migrations(self):
        """Run all pending migrations in order"""
        logger.info("🚀 Starting migration process...")

        migrations = [
            {
                "name": "001_add_integration_fields_to_analyses",
                "description": "Add integration_name and platform fields to analyses table",
                "sql": [
                    """
                    ALTER TABLE analyses
                    ADD COLUMN IF NOT EXISTS integration_name VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS platform VARCHAR(50)
                    """
                ]
            },
            {
                "name": "002_add_organization_id_to_user_correlations",
                "description": "Add organization_id to user_correlations for multi-tenancy support",
                "sql": [
                    """
                    ALTER TABLE user_correlations
                    ADD COLUMN IF NOT EXISTS organization_id INTEGER
                    """,
                    """
                    ALTER TABLE user_correlations
                    DROP CONSTRAINT IF EXISTS fk_user_correlations_organization
                    """,
                    """
                    ALTER TABLE user_correlations
                    ADD CONSTRAINT fk_user_correlations_organization
                    FOREIGN KEY (organization_id) REFERENCES organizations(id)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_correlations_organization_id
                    ON user_correlations(organization_id)
                    """,
                    """
                    UPDATE user_correlations uc
                    SET organization_id = u.organization_id
                    FROM users u
                    WHERE uc.user_id = u.id
                    AND uc.organization_id IS NULL
                    AND u.organization_id IS NOT NULL
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_correlations_org_email
                    ON user_correlations(organization_id, email)
                    """,
                    """
                    CREATE INDEX IF NOT EXISTS idx_user_correlations_org_slack
                    ON user_correlations(organization_id, slack_user_id)
                    WHERE slack_user_id IS NOT NULL
                    """
                ]
            },
            # Add future migrations here with incrementing numbers
            # {
            #     "name": "003_add_user_preferences",
            #     "description": "Add user preferences table",
            #     "sql": ["CREATE TABLE IF NOT EXISTS user_preferences (...)"]
            # }
        ]

        success_count = 0
        total_migrations = len(migrations)

        for migration in migrations:
            name = migration["name"]
            description = migration["description"]
            sql_commands = migration["sql"]

            logger.info(f"📋 Migration: {description}")

            if self.run_sql_migration(name, sql_commands):
                success_count += 1
            else:
                logger.error(f"❌ Migration failed: {name}")
                # Continue with other migrations instead of stopping
                continue

        logger.info(f"🎉 Migration process completed: {success_count}/{total_migrations} successful")

        if success_count == total_migrations:
            logger.info("✅ All migrations applied successfully!")
            return True
        else:
            logger.warning(f"⚠️  Some migrations failed: {total_migrations - success_count} failed")
            return False

    def get_migration_status(self):
        """Get status of all migrations"""
        try:
            result = self.db.execute(text("""
                SELECT name, applied_at, status
                FROM migrations
                ORDER BY applied_at
            """))

            migrations = []
            for row in result:
                migrations.append({
                    "name": row[0],
                    "applied_at": row[1],
                    "status": row[2]
                })

            logger.info(f"📊 Migration status: {len(migrations)} migrations applied")
            for migration in migrations:
                logger.info(f"  ✅ {migration['name']} - {migration['applied_at']}")

            return migrations

        except Exception as e:
            logger.error(f"❌ Failed to get migration status: {e}")
            return []

    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()

def run_migrations():
    """Main function to run all migrations"""
    runner = None
    try:
        runner = MigrationRunner()
        success = runner.run_all_migrations()
        runner.get_migration_status()
        return success

    except Exception as e:
        logger.error(f"❌ Migration system failed: {e}")
        return False

    finally:
        if runner:
            runner.close()

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)