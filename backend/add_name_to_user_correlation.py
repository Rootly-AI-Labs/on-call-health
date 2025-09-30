"""
Migration script to add 'name' column to user_correlations table.
Run this on Railway to update the database schema.
"""
import os
import sys
from sqlalchemy import create_engine, text

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

def add_name_column():
    """Add name column to user_correlations table."""
    engine = create_engine(settings.DATABASE_URL)

    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='user_correlations' AND column_name='name'
        """))

        if result.fetchone():
            print("✅ Column 'name' already exists in user_correlations table")
            return

        # Add the column
        print("Adding 'name' column to user_correlations table...")
        conn.execute(text("""
            ALTER TABLE user_correlations
            ADD COLUMN name VARCHAR(255)
        """))
        conn.commit()

        print("✅ Successfully added 'name' column to user_correlations table")
        print("   Users can now store display names from Rootly/PagerDuty")

if __name__ == "__main__":
    print("🔄 Starting migration: Add name column to user_correlations")
    try:
        add_name_column()
        print("✅ Migration complete!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)