"""
Migration script to add unique constraint on (user_id, email) in user_correlations table.
This prevents duplicate correlation records at the database level.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def add_unique_constraint():
    """Add unique constraint on (user_id, email) combination."""
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        # Check if constraint already exists
        result = conn.execute(text("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name='user_correlations'
            AND constraint_type='UNIQUE'
            AND constraint_name='uq_user_correlation_user_email'
        """))

        if result.fetchone():
            print("✅ Unique constraint already exists on user_correlations(user_id, email)")
            return

        # First, remove any existing duplicates (keep the most recent one)
        print("Checking for duplicate correlations...")
        conn.execute(text("""
            DELETE FROM user_correlations a
            USING user_correlations b
            WHERE a.id < b.id
            AND a.user_id = b.user_id
            AND a.email = b.email
        """))
        conn.commit()
        print("✅ Removed any duplicate correlations")

        # Add the unique constraint
        print("Adding unique constraint on (user_id, email)...")
        conn.execute(text("""
            ALTER TABLE user_correlations
            ADD CONSTRAINT uq_user_correlation_user_email
            UNIQUE (user_id, email)
        """))
        conn.commit()

        print("✅ Successfully added unique constraint to user_correlations table")
        print("   This prevents duplicate correlation records for the same user+email")

if __name__ == "__main__":
    print("🔄 Starting migration: Add unique constraint to user_correlations")
    try:
        add_unique_constraint()
        print("✅ Migration complete!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)