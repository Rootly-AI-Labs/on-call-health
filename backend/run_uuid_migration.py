#!/usr/bin/env python3
"""
One-time migration script to add UUID column to Railway PostgreSQL database.
Run this once after deployment: python run_uuid_migration.py
"""

import sys
import os

# Add the current directory to Python path so we can import our migration
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    try:
        from migrate_add_uuid_column import add_uuid_to_analyses
        print("Starting UUID migration for Railway PostgreSQL...")
        add_uuid_to_analyses()
        print("UUID migration completed successfully!")
    except ImportError as e:
        print(f"Error importing migration: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)