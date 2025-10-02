"""
Script to promote a user to org_admin role.
Usage: python promote_user_to_admin.py <user_email>
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_database_url():
    """Get database URL from environment variable."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Handle Railway's postgres:// to postgresql:// conversion
    if db_url.startswith('postgres://'):
        db_url = db_url.replace('postgres://', 'postgresql://', 1)

    return db_url

def promote_user(email: str):
    """Promote user to org_admin role."""
    database_url = get_database_url()
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find user by email
        result = session.execute(
            text("SELECT id, email, name, role FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()

        if not user:
            print(f"❌ User not found: {email}")
            return False

        print(f"\n📋 User found:")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name}")
        print(f"   Current role: {user.role}")

        if user.role == 'org_admin':
            print(f"\n✅ User is already an org_admin!")
            return True

        # Update role to org_admin
        session.execute(
            text("UPDATE users SET role = 'org_admin' WHERE id = :user_id"),
            {"user_id": user.id}
        )
        session.commit()

        print(f"\n✅ Successfully promoted {user.email} to org_admin!")
        print(f"   Old role: {user.role}")
        print(f"   New role: org_admin")

        return True

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {str(e)}")
        return False
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python promote_user_to_admin.py <user_email>")
        print("Example: python promote_user_to_admin.py spencer.cheng@rootly.com")
        sys.exit(1)

    email = sys.argv[1]
    print(f"\n{'='*70}")
    print(f"  Promoting User to Org Admin")
    print(f"{'='*70}\n")

    success = promote_user(email)

    if success:
        print("\n✅ Promotion complete! User can now:")
        print("   • Send surveys manually")
        print("   • Manage organization settings")
        print("   • Change other users' roles")
        print("\nℹ️  User may need to log out and log back in to see changes.\n")
        sys.exit(0)
    else:
        print("\n❌ Promotion failed.\n")
        sys.exit(1)
