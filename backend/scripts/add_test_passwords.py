"""
Add password authentication to test accounts for E2E testing.
Run this script to set passwords for test users.
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
import os

# Database connection - MUST be provided via environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is required.\n"
        "Example: DATABASE_URL='postgresql://user:pass@host:port/db' python scripts/add_test_passwords.py"
    )
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Test accounts
TEST_ACCOUNTS = [
    "avery.kim@oncallhealth.ai",
    "sam.rodriguez@oncallhealth.ai",
    "ethan.hart@oncallhealth.ai",
    "anika.shah@oncallhealth.ai",
]

TEST_PASSWORD = os.getenv("TEST_PASSWORD")
if not TEST_PASSWORD:
    raise ValueError(
        "TEST_PASSWORD environment variable is required.\n"
        "Example: TEST_PASSWORD='YourPassword' DATABASE_URL='...' python scripts/add_test_passwords.py"
    )

def hash_password(password: str) -> str:
    """Hash a password using bcrypt (matching auth.py implementation)."""
    # Ensure password fits in bcrypt's 72 byte limit
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]

    # Use bcrypt directly to match backend/app/api/endpoints/auth.py:937
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

def main():
    db = SessionLocal()
    try:
        password_hash = hash_password(TEST_PASSWORD)

        for email in TEST_ACCOUNTS:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.password_hash = password_hash
                print(f"✓ Added password to {email}")
            else:
                print(f"✗ User not found: {email}")

        db.commit()
        print(f"\n✓ Successfully added passwords to {len(TEST_ACCOUNTS)} test accounts")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
