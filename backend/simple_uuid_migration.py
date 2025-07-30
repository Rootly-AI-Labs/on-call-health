"""
Simple UUID migration using SQLAlchemy (should already be available)
"""
import os
import uuid
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def verify_database_connection():
    """Verify we can connect to the database"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: No DATABASE_URL found in environment variables")
        return None
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version}")
        return database_url
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def safe_uuid_migration():
    """UUID migration using SQLAlchemy"""
    print("🚀 Starting UUID Migration using SQLAlchemy")
    print("=" * 50)
    
    database_url = verify_database_connection()
    if not database_url:
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.begin() as conn:  # Automatic transaction
            # Check if uuid column exists
            result = conn.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name='analyses' AND column_name='uuid'
            """))
            uuid_exists = result.fetchone() is not None
            
            # Count analyses
            result = conn.execute(text("SELECT COUNT(*) FROM analyses"))
            total_analyses = result.fetchone()[0]
            
            print(f"📊 Found {total_analyses} analyses in database")
            print(f"📊 UUID column exists: {uuid_exists}")
            
            if uuid_exists:
                # Check how many have UUIDs
                result = conn.execute(text("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL"))
                with_uuid = result.fetchone()[0]
                print(f"📊 Analyses with UUIDs: {with_uuid}")
                
                if with_uuid == total_analyses:
                    print("✅ Migration already complete!")
                    return True
            
            # Add column if needed
            if not uuid_exists:
                print("🔄 Adding UUID column...")
                conn.execute(text("ALTER TABLE analyses ADD COLUMN uuid VARCHAR(36)"))
                print("✅ UUID column added")
            
            # Populate UUIDs
            result = conn.execute(text("SELECT id FROM analyses WHERE uuid IS NULL"))
            missing_ids = result.fetchall()
            
            if missing_ids:
                print(f"🔄 Populating {len(missing_ids)} analyses with UUIDs...")
                for (analysis_id,) in missing_ids:
                    new_uuid = str(uuid.uuid4())
                    conn.execute(text("UPDATE analyses SET uuid = :uuid WHERE id = :id"), 
                               {"uuid": new_uuid, "id": analysis_id})
                print(f"✅ Populated {len(missing_ids)} UUIDs")
            
            # Add constraints
            print("🔄 Adding constraints...")
            try:
                conn.execute(text("ALTER TABLE analyses ALTER COLUMN uuid SET NOT NULL"))
                print("✅ UUID column set to NOT NULL")
            except Exception as e:
                if "not-null constraint" not in str(e).lower():
                    raise
            
            try:
                conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_analyses_uuid ON analyses(uuid)"))
                print("✅ Unique index created")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    raise
            
            # Final verification
            result = conn.execute(text("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL"))
            final_count = result.fetchone()[0]
            
            if final_count == total_analyses:
                print(f"🎉 SUCCESS! All {total_analyses} analyses have UUIDs")
                return True
            else:
                raise Exception(f"Verification failed: {final_count}/{total_analyses} have UUIDs")
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    print("⚠️  WARNING: This will modify the PRODUCTION database!")
    confirm = input("Type 'YES' to continue: ")
    if confirm != "YES":
        print("❌ Cancelled")
        return
    
    success = safe_uuid_migration()
    if success:
        print("\n✅ MIGRATION COMPLETE!")
        print("Next: Uncomment UUID line in backend/app/models/analysis.py")
    else:
        print("\n❌ MIGRATION FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()