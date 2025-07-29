"""
Migration script to add UUID column to analyses table for PostgreSQL (Railway deployment)
"""
import os
import uuid
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def add_uuid_to_analyses():
    """Add UUID column to existing analyses table and populate with UUIDs"""
    
    # Get database URL from environment (Railway uses DATABASE_URL)
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("No DATABASE_URL found in environment variables")
        return
    
    try:
        # Connect to PostgreSQL database
        conn = psycopg2.connect(database_url)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if uuid column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='analyses' AND column_name='uuid'
        """)
        
        if cursor.fetchone():
            print("UUID column already exists")
            return
        
        print("Adding UUID column to analyses table...")
        
        # Add UUID column
        cursor.execute("ALTER TABLE analyses ADD COLUMN uuid VARCHAR(36)")
        
        # Create unique index
        cursor.execute("CREATE UNIQUE INDEX idx_analyses_uuid ON analyses(uuid)")
        
        # Populate existing records with UUIDs
        cursor.execute("SELECT id FROM analyses WHERE uuid IS NULL")
        analysis_ids = cursor.fetchall()
        
        print(f"Populating {len(analysis_ids)} existing analyses with UUIDs...")
        for (analysis_id,) in analysis_ids:
            new_uuid = str(uuid.uuid4())
            cursor.execute("UPDATE analyses SET uuid = %s WHERE id = %s", (new_uuid, analysis_id))
        
        # Make uuid column NOT NULL after populating
        cursor.execute("ALTER TABLE analyses ALTER COLUMN uuid SET NOT NULL")
        
        print("Migration completed successfully!")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"Verified: {count} analyses now have UUIDs")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_uuid_to_analyses()