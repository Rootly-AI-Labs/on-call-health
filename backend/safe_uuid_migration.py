"""
ULTRA-SAFE UUID Migration for Railway Production Database
Run this script to add UUID column to existing analyses table.
"""
import os
import uuid
import psycopg2
from psycopg2 import sql
import sys

def verify_database_connection():
    """Verify we can connect to the database"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: No DATABASE_URL found in environment variables")
        print("   Make sure you're running this in Railway environment or with correct env vars")
        return None
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✅ Connected to PostgreSQL: {version[0]}")
        conn.close()
        return database_url
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def check_existing_state(cursor):
    """Check current state of analyses table"""
    # Check if uuid column exists
    cursor.execute("""
        SELECT column_name, is_nullable, data_type 
        FROM information_schema.columns 
        WHERE table_name='analyses' AND column_name='uuid'
    """)
    uuid_column = cursor.fetchone()
    
    # Count total analyses
    cursor.execute("SELECT COUNT(*) FROM analyses")
    total_analyses = cursor.fetchone()[0]
    
    # Check if any analyses already have UUIDs
    uuid_count = 0
    if uuid_column:
        cursor.execute("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL")
        uuid_count = cursor.fetchone()[0]
    
    return {
        'uuid_column_exists': bool(uuid_column),
        'uuid_column_info': uuid_column,
        'total_analyses': total_analyses,
        'analyses_with_uuid': uuid_count
    }

def safe_uuid_migration():
    """
    Ultra-safe UUID migration with comprehensive error handling
    """
    print("🚀 Starting ULTRA-SAFE UUID Migration for Railway Database")
    print("=" * 60)
    
    # Step 1: Verify environment
    database_url = verify_database_connection()
    if not database_url:
        return False
    
    try:
        # Step 2: Connect with transaction control
        conn = psycopg2.connect(database_url)
        # Start a transaction (we'll commit manually)
        cursor = conn.cursor()
        
        # Step 3: Check current state
        print("📊 Checking current database state...")
        state = check_existing_state(cursor)
        
        print(f"   • Total analyses in database: {state['total_analyses']}")
        print(f"   • UUID column exists: {state['uuid_column_exists']}")
        print(f"   • Analyses with UUIDs: {state['analyses_with_uuid']}")
        
        # Step 4: Determine what needs to be done
        if state['uuid_column_exists'] and state['analyses_with_uuid'] == state['total_analyses']:
            print("✅ Migration already complete! All analyses have UUIDs.")
            return True
        
        if state['total_analyses'] == 0:
            print("ℹ️  No analyses in database. Migration will prepare for future records.")
        
        # Step 5: Begin transaction
        print("\n🔄 Starting migration transaction...")
        
        # Step 5a: Add UUID column if it doesn't exist
        if not state['uuid_column_exists']:
            print("   Adding UUID column...")
            cursor.execute("ALTER TABLE analyses ADD COLUMN uuid VARCHAR(36)")
            print("   ✅ UUID column added")
        
        # Step 5b: Populate UUIDs for records that don't have them
        if state['analyses_with_uuid'] < state['total_analyses']:
            missing_uuids = state['total_analyses'] - state['analyses_with_uuid']
            print(f"   Populating {missing_uuids} analyses with UUIDs...")
            
            # Get analyses without UUIDs
            cursor.execute("SELECT id FROM analyses WHERE uuid IS NULL")
            analysis_ids = cursor.fetchall()
            
            # Populate each with a UUID
            for i, (analysis_id,) in enumerate(analysis_ids):
                new_uuid = str(uuid.uuid4())
                cursor.execute("UPDATE analyses SET uuid = %s WHERE id = %s", (new_uuid, analysis_id))
                
                # Progress indicator for large datasets
                if i % 10 == 0 and i > 0:
                    print(f"   • Processed {i}/{len(analysis_ids)} records...")
            
            print(f"   ✅ Populated {len(analysis_ids)} analyses with UUIDs")
        
        # Step 5c: Add constraints and indexes
        print("   Adding database constraints...")
        
        # Make UUID column NOT NULL if it isn't already
        cursor.execute("""
            SELECT is_nullable FROM information_schema.columns 
            WHERE table_name='analyses' AND column_name='uuid'
        """)
        is_nullable = cursor.fetchone()[0]
        
        if is_nullable == 'YES':
            cursor.execute("ALTER TABLE analyses ALTER COLUMN uuid SET NOT NULL")
            print("   ✅ UUID column set to NOT NULL")
        
        # Add unique constraint/index if it doesn't exist
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'analyses' AND indexname LIKE '%uuid%'
        """)
        uuid_indexes = cursor.fetchall()
        
        if not uuid_indexes:
            cursor.execute("CREATE UNIQUE INDEX idx_analyses_uuid ON analyses(uuid)")
            print("   ✅ Unique index on UUID column created")
        
        # Step 6: Final verification
        print("\n🔍 Verifying migration...")
        
        final_state = check_existing_state(cursor)
        
        if (final_state['uuid_column_exists'] and 
            final_state['analyses_with_uuid'] == final_state['total_analyses'] and
            final_state['total_analyses'] >= 0):
            
            print("   ✅ All verifications passed!")
            print(f"   • {final_state['total_analyses']} analyses have UUIDs")
            print(f"   • UUID column properly configured")
            
            # Commit the transaction
            conn.commit()
            print("   ✅ Transaction committed successfully!")
            
            return True
        else:
            raise Exception("Verification failed - migration incomplete")
            
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED: {e}")
        try:
            conn.rollback()
            print("   🔄 Transaction rolled back - database unchanged")
        except:
            print("   ⚠️  Could not rollback transaction")
        return False
        
    finally:
        if 'conn' in locals():
            conn.close()
            print("   🔐 Database connection closed")

def main():
    """Main execution with safety prompts"""
    print("⚠️  WARNING: This will modify the PRODUCTION Railway database!")
    print("   Make sure you have:")
    print("   • ✅ Recent database backup")
    print("   • ✅ Verified this is the correct environment")
    print("   • ✅ Tested locally if possible")
    print()
    
    # Safety confirmation
    confirm = input("Type 'YES I UNDERSTAND' to proceed: ")
    if confirm != "YES I UNDERSTAND":
        print("❌ Migration cancelled")
        return
    
    success = safe_uuid_migration()
    
    if success:
        print("\n" + "=" * 60)
        print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        print()
        print("Next steps:")
        print("1. ✅ Uncomment UUID column in backend/app/models/analysis.py")
        print("2. ✅ Deploy backend code update")
        print("3. ✅ Test that both integer and UUID analysis IDs work")
        print("4. ✅ Monitor for any issues")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ MIGRATION FAILED")
        print("Database remains unchanged. Check error messages above.")
        print("=" * 60)
        sys.exit(1)

if __name__ == "__main__":
    main()