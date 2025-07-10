#!/usr/bin/env python3
"""
Database migration script for GitHub and Slack integration.
Adds tables for GitHub integrations, Slack integrations, and user correlations.
"""

import sqlite3
import sys
from pathlib import Path

def create_github_slack_tables():
    """Create tables for GitHub and Slack integrations."""
    
    # Connect to the database
    db_path = Path("app.db")
    if not db_path.exists():
        print("Error: app.db not found. Please run from the backend directory.")
        sys.exit(1)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Create GitHub integrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS github_integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                github_token TEXT,
                github_username TEXT NOT NULL,
                organizations TEXT, -- JSON array of organizations
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create Slack integrations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS slack_integrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                slack_token TEXT,
                slack_user_id TEXT NOT NULL,
                workspace_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create user correlations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_correlations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                github_username TEXT,
                slack_user_id TEXT,
                rootly_email TEXT,
                pagerduty_user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_github_user_id ON github_integrations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_github_username ON github_integrations(github_username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_user_id ON slack_integrations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_slack_user_id_workspace ON slack_integrations(slack_user_id, workspace_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_correlations_user_id ON user_correlations(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_correlations_email ON user_correlations(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_correlations_github ON user_correlations(github_username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_correlations_slack ON user_correlations(slack_user_id)")
        
        conn.commit()
        print("✅ Successfully created GitHub and Slack integration tables")
        
        # Verify tables were created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('github_integrations', 'slack_integrations', 'user_correlations')")
        tables = cursor.fetchall()
        
        if len(tables) == 3:
            print("✅ All integration tables created successfully:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print(f"⚠️  Warning: Expected 3 tables, found {len(tables)}")
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Main function to run the migration."""
    print("🚀 Starting GitHub and Slack integration migration...")
    create_github_slack_tables()
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    main()