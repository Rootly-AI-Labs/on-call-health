"""
Migration script to add UUID column to analyses table
"""
import sqlite3
import uuid
import os

def add_uuid_to_analyses():
    """Add UUID column to existing analyses table and populate with UUIDs"""
    db_path = 'test.db'
    
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if uuid column already exists
        cursor.execute("PRAGMA table_info(analyses)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'uuid' in columns:
            print("UUID column already exists")
            return
        
        # Add UUID column
        print("Adding UUID column to analyses table...")
        cursor.execute("ALTER TABLE analyses ADD COLUMN uuid VARCHAR(36)")
        
        # Create unique index
        cursor.execute("CREATE UNIQUE INDEX idx_analyses_uuid ON analyses(uuid)")
        
        # Populate existing records with UUIDs
        cursor.execute("SELECT id FROM analyses WHERE uuid IS NULL")
        analysis_ids = cursor.fetchall()
        
        print(f"Populating {len(analysis_ids)} existing analyses with UUIDs...")
        for (analysis_id,) in analysis_ids:
            new_uuid = str(uuid.uuid4())
            cursor.execute("UPDATE analyses SET uuid = ? WHERE id = ?", (new_uuid, analysis_id))
        
        # Make uuid column NOT NULL after populating
        # SQLite doesn't support ALTER COLUMN, so we'll leave it nullable for now
        # but ensure all new records have UUIDs via the model default
        
        conn.commit()
        print("Migration completed successfully!")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"Verified: {count} analyses now have UUIDs")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_uuid_to_analyses()