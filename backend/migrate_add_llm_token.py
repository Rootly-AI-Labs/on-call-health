#!/usr/bin/env python3
"""
Database migration to add LLM token fields to the users table.
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import text
from app.models.base import engine

def migrate_add_llm_token():
    """Add LLM token fields to users table."""
    
    print("🚀 Starting LLM token migration...")
    
    try:
        with engine.connect() as connection:
            # Check if columns already exist
            print("📋 Checking existing table structure...")
            
            # For SQLite, check if the columns exist
            result = connection.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            
            llm_token_exists = 'llm_token' in columns
            llm_provider_exists = 'llm_provider' in columns
            
            print(f"   • llm_token column exists: {llm_token_exists}")
            print(f"   • llm_provider column exists: {llm_provider_exists}")
            
            # Add llm_token column if it doesn't exist
            if not llm_token_exists:
                print("➕ Adding llm_token column...")
                connection.execute(text("ALTER TABLE users ADD COLUMN llm_token TEXT"))
                connection.commit()
                print("   ✅ llm_token column added successfully")
            else:
                print("   ⏭️ llm_token column already exists")
            
            # Add llm_provider column if it doesn't exist
            if not llm_provider_exists:
                print("➕ Adding llm_provider column...")
                connection.execute(text("ALTER TABLE users ADD COLUMN llm_provider VARCHAR(50)"))
                connection.commit()
                print("   ✅ llm_provider column added successfully")
            else:
                print("   ⏭️ llm_provider column already exists")
            
            # Verify the migration
            print("🔍 Verifying migration...")
            result = connection.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'llm_token' in columns and 'llm_provider' in columns:
                print("✅ Migration completed successfully!")
                print("   • llm_token column: ✅")
                print("   • llm_provider column: ✅")
                return True
            else:
                print("❌ Migration verification failed!")
                return False
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_add_llm_token()
    sys.exit(0 if success else 1)