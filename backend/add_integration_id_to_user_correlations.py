"""
Migration script to add integration_ids column to user_correlations table.

This script:
1. Adds integration_ids JSON column to user_correlations table
2. Allows users to belong to multiple organizations
3. Handles both PostgreSQL and SQLite databases

Run this script directly:
    python add_integration_id_to_user_correlations.py
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text, inspect
from app.models.base import engine, SessionLocal
from app.models.user_correlation import UserCorrelation

def check_column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_integration_id_column():
    """Add integration_ids JSON column to user_correlations table."""

    print("=" * 60)
    print("Migration: Add integration_ids to user_correlations")
    print("=" * 60)

    # Check if column already exists
    if check_column_exists('user_correlations', 'integration_ids'):
        print("✓ Column 'integration_ids' already exists in user_correlations table")
        print("  No migration needed.")
        return

    print("Adding 'integration_ids' JSON column to user_correlations table...")

    with engine.connect() as conn:
        try:
            # Add the column (JSON type for PostgreSQL, TEXT for SQLite)
            print("  - Adding column...")
            # Try PostgreSQL JSON type first
            try:
                conn.execute(text(
                    "ALTER TABLE user_correlations "
                    "ADD COLUMN integration_ids JSON"
                ))
                conn.commit()
            except Exception as e:
                # Fallback to JSONB for PostgreSQL or TEXT for SQLite
                print(f"    Note: {str(e)}")
                print("    Trying JSONB type...")
                conn.rollback()
                conn.execute(text(
                    "ALTER TABLE user_correlations "
                    "ADD COLUMN integration_ids JSONB"
                ))
                conn.commit()
            print("  ✓ Column added successfully")

            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            print("\nNext steps:")
            print("1. The integration_ids column is now available (JSON array)")
            print("2. Existing records have NULL integration_ids (backward compatible)")
            print("3. New syncs will populate integration_ids automatically")
            print("4. Users can now belong to multiple organizations")
            print("5. Re-sync users from each organization to populate integration_ids")

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
