#!/usr/bin/env python3
"""
Demo Analysis Management Script

Manages demo analysis data for all users. Can create new demo analyses for users
who don't have one, and update existing demo analyses with the latest mock data.

Usage:
    # Preview what would happen
    python manage_demo_analyses.py --dry-run

    # Create demo analyses for users who don't have one
    python manage_demo_analyses.py --create

    # Update existing demo analyses with latest mock data
    python manage_demo_analyses.py --update

    # Both create and update (full refresh)
    python manage_demo_analyses.py --refresh

    # Update a specific user's demo analysis
    python manage_demo_analyses.py --update --user-id 123

This script should be run whenever:
- mock_analysis_data.json is updated with new fields
- Schema changes require demo data updates
- New features need to be reflected in demo data
"""
import json
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

# Set DATABASE_URL in environment BEFORE importing models
if not os.getenv("DATABASE_URL"):
    from dotenv import load_dotenv
    load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from app.models.user import User
from app.models.analysis import Analysis


def load_mock_data(json_path: str) -> dict:
    """Load mock analysis data from JSON file."""
    print(f"[*] Loading mock data from: {json_path}")

    if not os.path.exists(json_path):
        print(f"[ERROR] Mock data file not found: {json_path}")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"[OK] Mock data loaded successfully")
    return data


def get_demo_analysis(db, user_id: int):
    """Get the demo analysis for a user, if it exists."""
    user_analyses = db.query(Analysis).filter(
        Analysis.user_id == user_id
    ).all()

    for analysis in user_analyses:
        if analysis.config and isinstance(analysis.config, dict):
            if analysis.config.get('is_demo') is True:
                return analysis
    return None


def create_demo_analysis(db, user: User, mock_data: dict, dry_run: bool = True) -> bool:
    """Create a demo analysis for a user who doesn't have one."""
    existing = get_demo_analysis(db, user.id)
    if existing:
        print(f"  [SKIP] User {user.id} ({user.email}) already has demo analysis #{existing.id}")
        return False

    original_analysis = mock_data['analysis']

    config = original_analysis.get('config', {}).copy()
    config['is_demo'] = True
    config['demo_created_at'] = datetime.now().isoformat()

    if dry_run:
        print(f"  [DRY-RUN] Would create demo analysis for user {user.id} ({user.email})")
        return True

    try:
        analysis = Analysis(
            user_id=user.id,
            organization_id=user.organization_id if hasattr(user, 'organization_id') else None,
            rootly_integration_id=None,
            integration_name="Demo Analysis",
            platform=original_analysis.get('platform', 'rootly'),
            time_range=original_analysis.get('time_range', 30),
            status="completed",
            config=config,
            results=original_analysis.get('results'),
            error_message=None,
            completed_at=datetime.now()
        )

        db.add(analysis)
        db.flush()

        print(f"  [OK] Created demo analysis #{analysis.id} for user {user.id} ({user.email})")
        return True

    except Exception as e:
        print(f"  [ERROR] Failed to create analysis for user {user.id}: {str(e)}")
        raise


def update_demo_analysis(db, analysis: Analysis, mock_data: dict, dry_run: bool = True) -> bool:
    """Update an existing demo analysis with the latest mock data."""
    original_analysis = mock_data['analysis']
    new_results = original_analysis.get('results')

    if dry_run:
        print(f"  [DRY-RUN] Would update demo analysis #{analysis.id} (user {analysis.user_id})")
        return True

    try:
        # Update the results with latest mock data
        analysis.results = new_results

        # Update config to track when it was last updated
        config = analysis.config.copy() if analysis.config else {}
        config['demo_updated_at'] = datetime.now().isoformat()
        analysis.config = config

        db.flush()

        print(f"  [OK] Updated demo analysis #{analysis.id} (user {analysis.user_id})")
        return True

    except Exception as e:
        print(f"  [ERROR] Failed to update analysis #{analysis.id}: {str(e)}")
        raise


def get_all_demo_analyses(db):
    """Get all demo analyses in the database."""
    all_analyses = db.query(Analysis).all()
    demo_analyses = []

    for analysis in all_analyses:
        if analysis.config and isinstance(analysis.config, dict):
            if analysis.config.get('is_demo') is True:
                demo_analyses.append(analysis)

    return demo_analyses


def main():
    parser = argparse.ArgumentParser(
        description='Manage demo analysis data for all users',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage_demo_analyses.py --dry-run          # Preview all changes
  python manage_demo_analyses.py --create           # Create missing demo analyses
  python manage_demo_analyses.py --update           # Update existing demo analyses
  python manage_demo_analyses.py --refresh          # Full refresh (create + update)
  python manage_demo_analyses.py --update --user-id 5  # Update specific user
        """
    )

    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without applying')
    parser.add_argument('--create', action='store_true',
                        help='Create demo analyses for users who do not have one')
    parser.add_argument('--update', action='store_true',
                        help='Update existing demo analyses with latest mock data')
    parser.add_argument('--refresh', action='store_true',
                        help='Full refresh: create missing and update existing')
    parser.add_argument('--user-id', type=int,
                        help='Target a specific user ID')
    parser.add_argument('--yes', '-y', action='store_true',
                        help='Skip confirmation prompt')

    args = parser.parse_args()

    # Validate arguments
    if not any([args.dry_run, args.create, args.update, args.refresh]):
        print("[ERROR] Please specify an action: --dry-run, --create, --update, or --refresh")
        parser.print_help()
        sys.exit(1)

    # --refresh is shorthand for --create --update
    if args.refresh:
        args.create = True
        args.update = True

    # Load mock data
    script_dir = Path(__file__).parent
    mock_data_path = script_dir / "mock_analysis_data.json"
    mock_data = load_mock_data(str(mock_data_path))

    # Connect to database
    print("[*] Connecting to database...")
    db = SessionLocal()

    try:
        created_count = 0
        updated_count = 0
        skipped_count = 0

        # Summary header
        mode = "DRY RUN" if args.dry_run else "APPLY"
        actions = []
        if args.create:
            actions.append("CREATE")
        if args.update:
            actions.append("UPDATE")

        print(f"\n{'='*60}")
        print(f"Mode: {mode} | Actions: {', '.join(actions)}")
        print(f"{'='*60}\n")

        # Confirmation for non-dry-run
        if not args.dry_run and not args.yes:
            response = input("Are you sure you want to proceed? (yes/no): ")
            if response.lower() != 'yes':
                print("[*] Cancelled by user")
                return

        if args.user_id:
            # Target specific user
            user = db.query(User).filter(User.id == args.user_id).first()
            if not user:
                print(f"[ERROR] User {args.user_id} not found")
                sys.exit(1)

            existing = get_demo_analysis(db, user.id)

            if args.update and existing:
                if update_demo_analysis(db, existing, mock_data, dry_run=args.dry_run):
                    updated_count += 1
            elif args.create and not existing:
                if create_demo_analysis(db, user, mock_data, dry_run=args.dry_run):
                    created_count += 1
            else:
                print(f"  [SKIP] No action needed for user {user.id}")
                skipped_count += 1
        else:
            # Process all users
            if args.update:
                print("[*] Updating existing demo analyses...")
                demo_analyses = get_all_demo_analyses(db)
                print(f"    Found {len(demo_analyses)} demo analyses to update\n")

                for analysis in demo_analyses:
                    if update_demo_analysis(db, analysis, mock_data, dry_run=args.dry_run):
                        updated_count += 1

            if args.create:
                print("\n[*] Creating demo analyses for users without one...")
                users = db.query(User).all()
                print(f"    Found {len(users)} total users\n")

                for user in users:
                    existing = get_demo_analysis(db, user.id)
                    if not existing:
                        if create_demo_analysis(db, user, mock_data, dry_run=args.dry_run):
                            created_count += 1
                    else:
                        skipped_count += 1

        # Commit changes
        if not args.dry_run:
            print("\n[*] Committing changes to database...")
            db.commit()
            print("[OK] Changes committed successfully")

        # Summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        if args.create:
            print(f"{'Would create' if args.dry_run else 'Created'}: {created_count} demo analyses")
        if args.update:
            print(f"{'Would update' if args.dry_run else 'Updated'}: {updated_count} demo analyses")
        print(f"Skipped: {skipped_count}")
        print(f"{'='*60}\n")

        if args.dry_run:
            print("[*] This was a dry run. No changes were made.")
            print("[*] Run without --dry-run to apply changes.")
        else:
            print("[OK] Demo analysis management completed successfully!")

    except Exception as e:
        print(f"\n[ERROR] An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()

        if not args.dry_run:
            print("[*] Rolling back changes...")
            db.rollback()
            print("[OK] Changes rolled back")

        sys.exit(1)

    finally:
        db.close()
        print("[*] Database connection closed")


if __name__ == "__main__":
    main()
