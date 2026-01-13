#!/usr/bin/env python3
"""
Clean up duplicate user_correlation records in the database.

This script identifies duplicate user_correlation records (same email + organization_id)
and keeps only the most complete record, preferring records with:
1. github_username set
2. slack_user_id set
3. jira_account_id set
4. Most recent created_at timestamp

Usage:
    python cleanup_duplicate_user_correlations.py [--dry-run] [--organization-id ORG_ID]
"""

import sys
import os
from pathlib import Path

# Add parent directory to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import argparse
from datetime import datetime

def get_database_url():
    """Get database URL from environment or use default."""
    return os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/railway')

def cleanup_duplicates(dry_run=True, organization_id=None):
    """
    Clean up duplicate user_correlation records.

    Args:
        dry_run: If True, only print what would be done without making changes
        organization_id: If provided, only clean up duplicates for this organization
    """
    engine = create_engine(get_database_url())
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find all duplicate email + organization_id combinations
        query = """
        SELECT email, organization_id, COUNT(*) as count
        FROM user_correlations
        WHERE 1=1
        """

        params = {}
        if organization_id:
            query += " AND organization_id = :org_id"
            params['org_id'] = organization_id

        query += """
        GROUP BY email, organization_id
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC, email
        """

        result = session.execute(text(query), params)
        duplicates = result.fetchall()

        if not duplicates:
            print("✅ No duplicate user_correlation records found!")
            return

        print(f"Found {len(duplicates)} email+org combinations with duplicates")
        print()

        total_deleted = 0

        for email, org_id, count in duplicates:
            print(f"📧 Processing: {email} (org {org_id}) - {count} records")

            # Get all records for this email + org
            get_records_query = """
            SELECT id, email, organization_id, user_id,
                   github_username, slack_user_id, jira_account_id,
                   linear_user_id, rootly_user_id, integration_ids,
                   created_at
            FROM user_correlations
            WHERE email = :email AND organization_id = :org_id
            ORDER BY
                CASE WHEN github_username IS NOT NULL THEN 1 ELSE 0 END DESC,
                CASE WHEN slack_user_id IS NOT NULL THEN 1 ELSE 0 END DESC,
                CASE WHEN jira_account_id IS NOT NULL THEN 1 ELSE 0 END DESC,
                CASE WHEN linear_user_id IS NOT NULL THEN 1 ELSE 0 END DESC,
                created_at DESC
            """

            records_result = session.execute(
                text(get_records_query),
                {'email': email, 'org_id': org_id}
            )
            records = records_result.fetchall()

            if len(records) <= 1:
                print("  ⚠️ Skipping - only 1 record found now")
                continue

            # Keep the first record (most complete based on ORDER BY)
            keep_record = records[0]
            delete_records = records[1:]

            print(f"  ✅ KEEP: ID={keep_record.id} | github={keep_record.github_username} | slack={keep_record.slack_user_id} | jira={keep_record.jira_account_id}")

            for record in delete_records:
                print(f"  ❌ DELETE: ID={record.id} | github={record.github_username} | slack={record.slack_user_id} | jira={record.jira_account_id}")

                if not dry_run:
                    delete_query = "DELETE FROM user_correlations WHERE id = :record_id"
                    session.execute(text(delete_query), {'record_id': record.id})
                    total_deleted += 1

            print()

        if not dry_run:
            session.commit()
            print(f"✅ Deleted {total_deleted} duplicate records")
        else:
            print(f"🔍 DRY RUN: Would delete {len([r for d in duplicates for r in range(d[2]-1)])} records")
            print("\nTo actually perform the cleanup, run with --execute flag")

    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description='Clean up duplicate user_correlation records')
    parser.add_argument('--execute', action='store_true',
                       help='Actually perform the cleanup (default is dry-run)')
    parser.add_argument('--organization-id', type=int,
                       help='Only clean up duplicates for this organization ID')

    args = parser.parse_args()

    dry_run = not args.execute

    if dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("   Use --execute to actually perform the cleanup")
    else:
        print("⚠️  EXECUTE MODE - Changes will be made to the database!")
        response = input("Are you sure you want to continue? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return

    print()
    cleanup_duplicates(dry_run=dry_run, organization_id=args.organization_id)

if __name__ == '__main__':
    main()
