#!/usr/bin/env python3
"""
Database migration to add token_source column to github_integrations and slack_integrations tables
"""
import sqlite3
import os
from pathlib import Path

def migrate_database():
    """Add missing token_source columns to integration tables"""
    
    # Get database path
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "test.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return False
    
    print(f"Migrating database at {db_path}")
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if github_integrations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='github_integrations'
        """)
        if cursor.fetchone():
            print("Found github_integrations table")
            
            # Check if token_source column exists
            cursor.execute("PRAGMA table_info(github_integrations)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'token_source' not in columns:
                print("Adding token_source column to github_integrations table...")
                cursor.execute("""
                    ALTER TABLE github_integrations 
                    ADD COLUMN token_source VARCHAR(20) DEFAULT 'oauth'
                """)
                print("✅ Added token_source column to github_integrations")
            else:
                print("✅ token_source column already exists in github_integrations")
        
        # Check if slack_integrations table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='slack_integrations'
        """)
        if cursor.fetchone():
            print("Found slack_integrations table")
            
            # Check if token_source column exists
            cursor.execute("PRAGMA table_info(slack_integrations)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'token_source' not in columns:
                print("Adding token_source column to slack_integrations table...")
                cursor.execute("""
                    ALTER TABLE slack_integrations 
                    ADD COLUMN token_source VARCHAR(20) DEFAULT 'oauth'
                """)
                print("✅ Added token_source column to slack_integrations")
            else:
                print("✅ token_source column already exists in slack_integrations")
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully")
        
        # Verify the changes
        cursor.execute("PRAGMA table_info(github_integrations)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"GitHub integrations columns: {columns}")
        
        cursor.execute("PRAGMA table_info(slack_integrations)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Slack integrations columns: {columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        print("\n🎉 Database migration completed successfully!")
        print("You can now test the GitHub integration again.")
    else:
        print("\n💥 Migration failed. Please check the errors above.")