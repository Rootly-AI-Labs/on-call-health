"""
Migration script to add personal_circumstances column to user_burnout_reports table.

This migration adds support for tracking non-work factors (e.g., poor sleep, family issues)
that may influence burnout survey responses, helping separate contextual factors from
organizational burnout causes.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def get_database_url():
    """Get database URL from environment variable."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Handle Railway's postgres:// to postgresql:// conversion
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    return db_url

def add_personal_circumstances_column():
    """Add personal_circumstances column to user_burnout_reports table."""
    database_url = get_database_url()
    engine = create_engine(database_url)

    print("🔄 Starting migration: Add personal_circumstances column")
    print(f"📊 Database: {database_url.split('@')[1] if '@' in database_url else 'local'}")

    try:
        with engine.connect() as conn:
            # Check if column already exists
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'user_burnout_reports'
                AND column_name = 'personal_circumstances'
            """)

            result = conn.execute(check_sql)
            if result.fetchone():
                print("✅ Column 'personal_circumstances' already exists - skipping")
                return True

            # Add the column
            add_column_sql = text("""
                ALTER TABLE user_burnout_reports
                ADD COLUMN personal_circumstances VARCHAR(20);
            """)

            conn.execute(add_column_sql)
            conn.commit()

            print("✅ Successfully added 'personal_circumstances' column")
            print("   Column type: VARCHAR(20)")
            print("   Nullable: TRUE (optional field)")
            print("   Values: 'significantly', 'somewhat', 'no', 'prefer_not_say'")

            return True

    except SQLAlchemyError as e:
        print(f"❌ Migration failed: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  Personal Circumstances Column Migration")
    print("="*70 + "\n")

    success = add_personal_circumstances_column()

    if success:
        print("\n✅ Migration completed successfully!")
        print("\nℹ️  Users can now indicate if personal circumstances (sleep, family)")
        print("   are affecting their burnout responses, helping separate contextual")
        print("   factors from organizational causes.\n")
        sys.exit(0)
    else:
        print("\n❌ Migration failed. Please check the error messages above.\n")
        sys.exit(1)
