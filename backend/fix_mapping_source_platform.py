#!/usr/bin/env python3
"""
Fix missing source_platform values in user_mappings table.

This script updates all user_mappings where source_platform is NULL
and sets it to 'rootly' since most mappings are from Rootly users.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings
from app.models.user_mapping import UserMapping

def main():
    # Create database connection
    engine = create_engine(str(settings.DATABASE_URL))
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("🔍 Checking for mappings with NULL source_platform...")
        
        # Find mappings with NULL source_platform
        null_mappings = db.query(UserMapping).filter(UserMapping.source_platform.is_(None)).all()
        
        print(f"📊 Found {len(null_mappings)} mappings with NULL source_platform")
        
        if len(null_mappings) == 0:
            print("✅ No mappings need fixing!")
            return
        
        # Show some examples
        print("\n📋 Sample mappings to fix:")
        for i, mapping in enumerate(null_mappings[:5]):
            print(f"  {i+1}. ID:{mapping.id} | NULL:{mapping.source_identifier} -> {mapping.target_platform}:{mapping.target_identifier}")
        
        if len(null_mappings) > 5:
            print(f"  ... and {len(null_mappings) - 5} more")
        
        # Ask for confirmation
        response = input(f"\n❓ Update all {len(null_mappings)} mappings to have source_platform='rootly'? (y/N): ")
        
        if response.lower() != 'y':
            print("❌ Cancelled - no changes made")
            return
        
        print("\n🔧 Updating mappings...")
        
        # Update all NULL source_platform to 'rootly'
        updated_count = db.query(UserMapping).filter(
            UserMapping.source_platform.is_(None)
        ).update({
            'source_platform': 'rootly'
        })
        
        db.commit()
        
        print(f"✅ Successfully updated {updated_count} mappings!")
        print("   All mappings now have source_platform='rootly'")
        
        # Verify the fix
        remaining_null = db.query(UserMapping).filter(UserMapping.source_platform.is_(None)).count()
        print(f"🔍 Verification: {remaining_null} mappings still have NULL source_platform")
        
        if remaining_null == 0:
            print("🎉 All mappings fixed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()