"""
Migration script to update existing survey schedule messages to time-agnostic greeting.

This script updates all existing survey_schedules records that still have the old
"Good morning!" message to the new "Hi there!" message.

Run this script directly:
    python update_survey_messages.py
"""

import sys
import os

# Add the parent directory to the path so we can import from app
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.models.base import engine

def update_survey_messages():
    """Update existing survey schedule messages."""

    print("=" * 60)
    print("Migration: Update survey messages to time-agnostic greeting")
    print("=" * 60)

    with engine.connect() as conn:
        try:
            # Check if survey_schedules table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'survey_schedules'
                )
            """))
            table_exists = result.scalar()

            if not table_exists:
                print("✓ survey_schedules table does not exist yet, skipping...")
                return

            # Update old "Good morning!" messages to "Hi there!"
            print("Updating message templates...")

            # Update main message template
            result = conn.execute(text("""
                UPDATE survey_schedules
                SET message_template = 'Hi there! 👋

Quick check-in: How are you doing today?

Your feedback helps us support team health and prevent burnout.'
                WHERE message_template LIKE 'Good morning!%'
            """))
            updated_count = result.rowcount
            conn.commit()

            print(f"✓ Updated {updated_count} survey schedule(s)")

            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)

        except Exception as e:
            conn.rollback()
            print(f"\n✗ Error during migration: {str(e)}")
            raise

if __name__ == "__main__":
    try:
        update_survey_messages()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nMigration failed: {str(e)}")
        sys.exit(1)
