"""
Migration script to add integration_id column to user_correlations table.

This script:
1. Adds integration_id column to user_correlations table
2. Creates an index on integration_id for query performance
3. Handles both PostgreSQL and SQLite databases

Run this script directly:
    python add_integration_id_to_user_correlations.py
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from app.database import engine, SessionLocal
from app.models.user_correlation import UserCorrelation

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_integration_id_column():
    """Add integration_id column to user_correlations table."""

    print("=" * 60)
    print("Migration: Add integration_id to user_correlations")
    print("=" * 60)

    # Check if column already exists
    if check_column_exists('user_correlations', 'integration_id'):
        print("✓ Column 'integration_id' already exists in user_correlations table")
        print("  No migration needed.")
        return

    print("Adding 'integration_id' column to user_correlations table...")

    with engine.connect() as conn:
        try:
            # Add the column
            print("  - Adding column...")
            conn.execute(text(
                "ALTER TABLE user_correlations "
                "ADD COLUMN integration_id VARCHAR(100)"
            ))
            conn.commit()
            print("  ✓ Column added successfully")

            # Create index
            print("  - Creating index on integration_id...")
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS idx_user_correlations_integration_id "
                "ON user_correlations(integration_id)"
            ))
            conn.commit()
            print("  ✓ Index created successfully")

            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. The integration_id column is now available")
            print("2. Existing records have NULL integration_id (backward compatible)")
            print("3. New syncs will populate integration_id automatically")
            print("4. Re-sync users from each organization to populate integration_id")

        except Exception as e:
            conn.rollback()
            print(f"\n✗ Error during migration: {str(e)}")
            print("\nIf the error is about the column already existing, you can safely ignore it.")
            raise

if __name__ == "__main__":
    try:
        add_integration_id_column()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nMigration failed: {str(e)}")
        sys.exit(1)
