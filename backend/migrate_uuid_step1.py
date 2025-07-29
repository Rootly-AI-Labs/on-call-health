"""
Step 1: Add UUID column to database (run this FIRST on Railway)
"""
import os
import uuid
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def add_uuid_column_only():
    """Add UUID column to existing analyses table without modifying model"""
    
    # Get database URL from environment (Railway uses DATABASE_URL)
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("No DATABASE_URL found in environment variables")
        return False
    
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
            return True
        
        print("Adding UUID column to analyses table...")
        
        # Add UUID column (nullable initially)
        cursor.execute("ALTER TABLE analyses ADD COLUMN uuid VARCHAR(36)")
        
        # Populate existing records with UUIDs
        cursor.execute("SELECT id FROM analyses")
        analysis_ids = cursor.fetchall()
        
        print(f"Populating {len(analysis_ids)} existing analyses with UUIDs...")
        for (analysis_id,) in analysis_ids:
            new_uuid = str(uuid.uuid4())
            cursor.execute("UPDATE analyses SET uuid = %s WHERE id = %s", (new_uuid, analysis_id))
        
        # Make uuid column NOT NULL and add unique constraint
        cursor.execute("ALTER TABLE analyses ALTER COLUMN uuid SET NOT NULL")
        cursor.execute("CREATE UNIQUE INDEX idx_analyses_uuid ON analyses(uuid)")
        
        print("Migration completed successfully!")
        
        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL")
        count = cursor.fetchone()[0]
        print(f"Verified: {count} analyses now have UUIDs")
        
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = add_uuid_column_only()
    if success:
        print("\n✅ Step 1 complete! The UUID column has been added to the database.")
        print("   Next: Deploy the code update that includes the UUID field in the model.")
    else:
        print("\n❌ Migration failed. Please check the error messages above.")