#!/usr/bin/env python3
"""
Railway-specific UUID migration runner
This script ensures proper environment setup for Railway deployment
"""
import os
import sys

def setup_railway_environment():
    """Set up environment for Railway"""
    # Railway automatically sets DATABASE_URL, but let's verify
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL not found")
        print("   This script should be run in Railway environment")
        print("   Or manually set DATABASE_URL environment variable")
        return False
    
    # Add backend to Python path for imports
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    
    return True

def main():
    if not setup_railway_environment():
        sys.exit(1)
    
    # Import and run the migration
    from safe_uuid_migration import main as run_migration
    run_migration()

if __name__ == "__main__":
    main()