"""
Migration script to add platform column to rootly_integrations table.
"""

import sqlite3
import sys

def migrate_database(db_path: str = "app.db"):
    """Add platform column to rootly_integrations table."""
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(rootly_integrations)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "platform" in columns:
            print("✓ Platform column already exists")
        else:
            print("Adding platform column...")
            
            # Add platform column with default value
            cursor.execute("""
                ALTER TABLE rootly_integrations 
                ADD COLUMN platform VARCHAR(50) NOT NULL DEFAULT 'rootly'
            """)
            print("✓ Added platform column")
        
        # Check for token vs api_token column
        if "token" in columns and "api_token" not in columns:
            print("Renaming token column to api_token...")
            
            # SQLite doesn't support direct column rename, so we need to recreate the table
            cursor.execute("""
                CREATE TABLE rootly_integrations_new (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    organization_name VARCHAR(255),
                    api_token TEXT NOT NULL,
                    platform VARCHAR(50) NOT NULL DEFAULT 'rootly',
                    total_users INTEGER,
                    is_default BOOLEAN NOT NULL DEFAULT 0,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Copy data
            cursor.execute("""
                INSERT INTO rootly_integrations_new 
                (id, user_id, name, organization_name, api_token, platform, 
                 total_users, is_default, is_active, created_at, last_used_at)
                SELECT id, user_id, name, organization_name, token, 'rootly',
                       total_users, is_default, is_active, created_at, last_used_at
                FROM rootly_integrations
            """)
            
            # Drop old table and rename new one
            cursor.execute("DROP TABLE rootly_integrations")
            cursor.execute("ALTER TABLE rootly_integrations_new RENAME TO rootly_integrations")
            
            print("✓ Renamed token column to api_token")
        elif "api_token" in columns:
            print("✓ api_token column already exists")
        
        # Commit changes
        conn.commit()
        print("\n✅ Migration completed successfully!")
        
        # Show current integrations
        cursor.execute("SELECT COUNT(*) FROM rootly_integrations WHERE platform = 'rootly'")
        rootly_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM rootly_integrations WHERE platform = 'pagerduty'")
        pagerduty_count = cursor.fetchone()[0]
        
        print(f"\nCurrent integrations:")
        print(f"  - Rootly: {rootly_count}")
        print(f"  - PagerDuty: {pagerduty_count}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate_database()