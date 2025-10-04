#!/usr/bin/env python3
"""
Make slack_user_id nullable in slack_integrations table.
This is needed for OAuth bot tokens which don't have a specific user ID.
"""
import sys
sys.path.insert(0, 'app')

from app.models import get_db
from sqlalchemy import text

def run_migration():
    """Make slack_user_id column nullable"""
    db = next(get_db())

    try:
        print("🔄 Making slack_user_id nullable in slack_integrations table...")

        # Check if column is already nullable
        check_sql = """
        SELECT is_nullable
        FROM information_schema.columns
        WHERE table_name = 'slack_integrations'
        AND column_name = 'slack_user_id'
        """
        result = db.execute(text(check_sql))
        row = result.fetchone()

        if row and row[0] == 'YES':
            print("✅ Column is already nullable - skipping migration")
            return True

        # Make the column nullable
        alter_sql = """
        ALTER TABLE slack_integrations
        ALTER COLUMN slack_user_id DROP NOT NULL
        """
        db.execute(text(alter_sql))
        db.commit()

        print("✅ Successfully made slack_user_id nullable")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
