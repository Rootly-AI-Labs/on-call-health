#!/usr/bin/env python3
"""
Manual migration runner for immediate deployment

This script can be run manually to apply migrations immediately
without waiting for a full deployment.
"""

from migrations.migration_runner import run_migrations

if __name__ == "__main__":
    print("🚀 Manual migration runner starting...")
    success = run_migrations()

    if success:
        print("🎉 All migrations completed successfully!")
        print("✅ Your database schema is now up to date")
    else:
        print("❌ Some migrations failed - check the logs above")
        print("💡 You may need to run this again or check database permissions")

    exit(0 if success else 1)