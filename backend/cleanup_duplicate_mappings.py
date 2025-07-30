#!/usr/bin/env python3
"""
Cleanup script to remove duplicate GitHub mappings from IntegrationMapping table.

This script safely removes duplicate mappings that were created before Phase 1 fixes,
keeping only the most recent mapping for each user-email combination.
"""
import os
import sys
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend path to sys.path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

try:
    from app.models import IntegrationMapping, get_db
    from app.services.mapping_recorder import MappingRecorder
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're running this from the backend directory")
    sys.exit(1)

def get_database_url():
    """Get database URL from environment or Railway."""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not found")
        print("For Railway: railway run python cleanup_duplicate_mappings.py")
        sys.exit(1)
    return database_url

def cleanup_duplicate_mappings():
    """Remove duplicate GitHub mappings, keeping only the most recent for each user-email."""
    database_url = get_database_url()
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as db:
        print("🧹 Starting duplicate mapping cleanup...")
        
        # Get all GitHub mappings grouped by user_id and source_identifier (email)
        query = text("""
        SELECT user_id, source_identifier, COUNT(*) as duplicate_count,
               array_agg(id ORDER BY created_at DESC) as mapping_ids,
               array_agg(target_identifier ORDER BY created_at DESC) as usernames,
               array_agg(mapping_successful ORDER BY created_at DESC) as success_flags,
               array_agg(created_at ORDER BY created_at DESC) as created_dates
        FROM integration_mappings 
        WHERE target_platform = 'github'
        GROUP BY user_id, source_identifier 
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        """)
        
        duplicates = db.execute(query).fetchall()
        
        if not duplicates:
            print("✅ No duplicate mappings found!")
            return
        
        print(f"🔍 Found {len(duplicates)} email addresses with duplicate mappings")
        
        total_to_delete = 0
        kept_mappings = 0
        
        for row in duplicates:
            user_id = row[0]
            email = row[1] 
            duplicate_count = row[2]
            mapping_ids = row[3]  # Already sorted by created_at DESC
            usernames = row[4]
            success_flags = row[5]
            created_dates = row[6]
            
            print(f"\n📧 {email} (User {user_id}): {duplicate_count} duplicates")
            
            # Keep the most recent mapping (first in the DESC ordered array)
            keep_id = mapping_ids[0]
            keep_username = usernames[0] 
            keep_success = success_flags[0]
            keep_date = created_dates[0]
            
            # Delete the older mappings (rest of the array)
            delete_ids = mapping_ids[1:]
            
            print(f"  ✅ KEEPING: ID {keep_id} -> {keep_username} ({'Success' if keep_success else 'Failed'}) from {keep_date}")
            
            for i, delete_id in enumerate(delete_ids, 1):
                delete_username = usernames[i]
                delete_success = success_flags[i] 
                delete_date = created_dates[i]
                print(f"  🗑️  DELETING: ID {delete_id} -> {delete_username} ({'Success' if delete_success else 'Failed'}) from {delete_date}")
            
            # Execute the deletion
            delete_query = text("DELETE FROM integration_mappings WHERE id = ANY(:ids)")
            result = db.execute(delete_query, {"ids": delete_ids})
            deleted_count = result.rowcount
            
            total_to_delete += deleted_count
            kept_mappings += 1
            
            print(f"  ✅ Deleted {deleted_count} duplicate mappings for {email}")
        
        # Commit all deletions
        db.commit()
        
        print(f"\n🎉 CLEANUP COMPLETE!")
        print(f"   📧 Processed: {len(duplicates)} email addresses")  
        print(f"   ✅ Kept: {kept_mappings} most recent mappings")
        print(f"   🗑️  Deleted: {total_to_delete} duplicate mappings")
        
        # Verify cleanup worked
        verify_query = text("""
        SELECT COUNT(*) as remaining_duplicates
        FROM (
            SELECT user_id, source_identifier, COUNT(*) as cnt
            FROM integration_mappings 
            WHERE target_platform = 'github'
            GROUP BY user_id, source_identifier 
            HAVING COUNT(*) > 1
        ) duplicates
        """)
        
        remaining = db.execute(verify_query).fetchone()[0]
        
        if remaining == 0:
            print(f"   ✅ Verification: No duplicates remaining!")
        else:
            print(f"   ⚠️  Verification: {remaining} duplicate groups still exist")
        
        print(f"\n📊 Next steps:")
        print(f"   1. Run a new burnout analysis")
        print(f"   2. Check GitHub Data Mapping modal")
        print(f"   3. Verify each team member appears only once")

if __name__ == "__main__":
    print("🧹 GitHub Mapping Duplicate Cleanup Tool")
    print("=" * 50)
    
    try:
        cleanup_duplicate_mappings()
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)