#!/usr/bin/env python3
"""
Migration to add webhook_url field to slack_integrations table.
"""
import sqlite3
import os

def run_migration():
    """Add webhook_url column to slack_integrations table."""
    db_path = os.path.join(os.path.dirname(__file__), "test.db")
    
    if not os.path.exists(db_path):
        print("Database file not found. Creating tables first...")
        # Run the main app to create tables
        import sys
        sys.path.append(os.path.dirname(__file__))
        from app.models import Base, engine
        Base.metadata.create_all(bind=engine)
        print("Tables created.")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if webhook_url column already exists
        cursor.execute("PRAGMA table_info(slack_integrations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'webhook_url' not in columns:
            print("Adding webhook_url column to slack_integrations table...")
            cursor.execute("ALTER TABLE slack_integrations ADD COLUMN webhook_url TEXT")
            conn.commit()
            print("✅ webhook_url column added successfully!")
        else:
            print("ℹ️  webhook_url column already exists.")
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()