"""
Ensure rootly.com organization exists and all rootly.com users are assigned to it.

This fixes:
1. Users showing as "Member" instead of "Admin"
2. "Organization required to sync Slack user IDs" error

Run with --dry-run to see what would change without making changes.
"""
import sys
import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Import models
sys.path.append('/Users/spencercheng/Workspace/Rootly/rootly-burnout-detector-web/backend')
from app.models.user import User
from app.models.organization import Organization
from app.core.config import settings

def ensure_rootly_org(dry_run=True):
    # Create database engine
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    changes = []

    try:
        print(f"Database: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'local'}")
        print("=" * 80)

        # Check for rootly.com organization
        rootly_org = db.query(Organization).filter(
            Organization.domain == 'rootly.com'
        ).first()

        if not rootly_org:
            changes.append("CREATE rootly.com organization")
            print("\n❌ No rootly.com organization found!")
            print("   Will create: Organization(name='Rootly', domain='rootly.com', status='active')")

            if not dry_run:
                rootly_org = Organization(
                    name="Rootly",
                    domain="rootly.com",
                    status="active",
                    created_at=datetime.now()
                )
                db.add(rootly_org)
                db.flush()  # Get the ID without committing
                print(f"   ✓ Created organization ID: {rootly_org.id}")
        else:
            print(f"\n✓ Found rootly.com organization (ID: {rootly_org.id})")

        # Find rootly.com users without proper setup
        rootly_users = db.query(User).filter(
            User.email.like('%@rootly.com')
        ).all()

        if not rootly_users:
            print("\n✓ No rootly.com users found")
            if dry_run:
                print("\n🔍 DRY RUN - No changes made")
            return

        print(f"\nFound {len(rootly_users)} rootly.com users:")
        print("-" * 80)

        for user in rootly_users:
            user_changes = []
            print(f"\n{user.name} ({user.email})")
            print(f"  Current org_id: {user.organization_id}")
            print(f"  Current role: {user.role}")

            # Fix organization_id
            if not user.organization_id and rootly_org:
                user_changes.append(f"  → Set organization_id = {rootly_org.id}")
                if not dry_run:
                    user.organization_id = rootly_org.id
                    user.joined_org_at = datetime.now()

            # Fix role (beta: everyone is org_admin)
            if user.role != 'org_admin':
                user_changes.append(f"  → Set role = 'org_admin' (was: {user.role})")
                if not dry_run:
                    user.role = 'org_admin'

            if user_changes:
                changes.extend(user_changes)
                for change in user_changes:
                    print(change)
            else:
                print("  ✓ No changes needed")

        if changes:
            print("\n" + "=" * 80)
            print(f"Summary: {len(changes)} changes")
            for change in changes:
                print(f"  • {change}")

            if dry_run:
                print("\n🔍 DRY RUN - No changes were made to the database")
                print("   Run without --dry-run to apply changes")
                db.rollback()
            else:
                db.commit()
                print("\n✅ All changes committed to database")
                print("\n⚠️  Users need to log out and log back in to see changes")
        else:
            print("\n✓ No changes needed - all users properly configured")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ensure rootly.com organization exists")
    parser.add_argument('--dry-run', action='store_true', default=True,
                        help='Show what would change without making changes (default)')
    parser.add_argument('--apply', action='store_true',
                        help='Actually apply the changes to the database')
    args = parser.parse_args()

    # If --apply is used, turn off dry-run
    dry_run = not args.apply

    print("Rootly Organization Setup")
    print("=" * 80)
    if dry_run:
        print("MODE: DRY RUN (use --apply to make actual changes)")
    else:
        print("MODE: APPLY CHANGES")
        confirm = input("\n⚠️  This will modify the database. Continue? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            sys.exit(0)

    print()
    ensure_rootly_org(dry_run=dry_run)
