"""
Migration script to fix organizations with status=None
Sets all organizations with NULL status to 'active'
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.models import get_db, SessionLocal
from app.models.organization import Organization
from sqlalchemy import text

def fix_organization_status():
    """Fix organizations with NULL status by setting to 'active'"""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("FIXING ORGANIZATION STATUS")
        print("=" * 60)

        # Check current status of all organizations
        print("\n📊 Current organization statuses:")
        organizations = db.query(Organization).all()

        for org in organizations:
            print(f"  - {org.name} (ID: {org.id})")
            print(f"    Status: {org.status}")
            print(f"    Domain: {org.domain}")
            print()

        # Find organizations with NULL status
        null_status_orgs = db.query(Organization).filter(
            Organization.status == None
        ).all()

        if not null_status_orgs:
            print("✅ All organizations have a status set!")
            return

        print(f"\n🔧 Found {len(null_status_orgs)} organizations with NULL status")
        print("Setting status to 'active'...\n")

        # Fix each organization
        for org in null_status_orgs:
            print(f"  Fixing: {org.name} (ID: {org.id})")
            org.status = 'active'

        # Commit changes
        db.commit()
        print(f"\n✅ Successfully updated {len(null_status_orgs)} organizations!")

        # Verify the fix
        print("\n📊 Updated organization statuses:")
        organizations = db.query(Organization).all()

        for org in organizations:
            print(f"  - {org.name} (ID: {org.id})")
            print(f"    Status: {org.status} ✓")
            print(f"    Domain: {org.domain}")
            print()

        print("=" * 60)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 60)
        print("\nYou can now use the /burnout-survey command in Slack!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    fix_organization_status()
