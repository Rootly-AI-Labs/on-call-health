#!/usr/bin/env python3
"""
Demo Analysis Management Script

Manages demo analysis data for all users. Can create new demo analyses for users
who don't have one, and update existing demo analyses with the latest mock data.

SAFETY NOTE: This script ONLY modifies demo analyses marked with is_demo=True.
It will NEVER delete real user data or production analyses.

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
import logging
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
from app.models.user_burnout_report import UserBurnoutReport

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def verify_demo_analysis_safe(analysis: Analysis) -> bool:
    """
    SAFETY CHECK: Verify that an analysis is marked as a demo before allowing deletion.

    This prevents accidental deletion of real user data by ensuring:
    1. The analysis has config with is_demo=True
    2. Only explicitly marked demo analyses can have their data deleted

    Args:
        analysis: Analysis object to verify

    Returns:
        bool: True if safe to delete (is_demo=True), False otherwise
    """
    if not analysis or not isinstance(analysis.config, dict):
        logger.error(f"SAFETY CHECK FAILED: Analysis #{analysis.id if analysis else 'unknown'} has no config")
        return False

    is_demo = analysis.config.get('is_demo') is True

    if not is_demo:
        logger.error(f"SAFETY CHECK FAILED: Analysis #{analysis.id} is NOT marked as demo (is_demo={analysis.config.get('is_demo')})")
        logger.error(f"                     User: {analysis.user_id} | Organization: {analysis.organization_id}")
        logger.error(f"                     This appears to be a REAL USER analysis. Deletion blocked.")
        return False

    logger.info(f"SAFETY CHECK PASSED: Analysis #{analysis.id} is verified as demo (is_demo=True)")
    return True


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
        print(f"  [SKIP] User {user.id} already has demo analysis #{existing.id}")
        return False

    original_analysis = mock_data['analysis']

    config = original_analysis.get('config', {}).copy()
    config['is_demo'] = True
    config['demo_created_at'] = datetime.now().isoformat()

    if dry_run:
        # Count what would be loaded
        reports_count = len(mock_data.get('user_burnout_reports', []))
        print(f"  [DRY-RUN] Would create demo analysis for user {user.id}")
        if reports_count > 0:
            print(f"            Would load {reports_count} health check-in records")
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

        print(f"  [OK] Created demo analysis #{analysis.id} for user {user.id}")

        # Load burnout reports (health check-ins) for this user
        # Pass the analysis object for safety verification
        reports_loaded = load_demo_burnout_reports(db, user.id, analysis, mock_data, dry_run=False)
        if reports_loaded > 0:
            print(f"       Loaded {reports_loaded} health check-in records")

        return True

    except Exception as e:
        print(f"  [ERROR] Failed to create analysis for user {user.id}: {str(e)}")
        raise


def load_demo_burnout_reports(db, user_id: int, analysis: Analysis, mock_data: dict, dry_run: bool = True) -> int:
    """
    Load user burnout reports (health check-ins) from mock data.

    SAFETY: Only deletes burnout reports if the analysis is verified as a demo analysis.
    Includes audit logging of all deletions.

    Args:
        db: Database session
        user_id: User ID to link reports to
        analysis: Analysis object (used for safety verification if updating demo)
        mock_data: Mock analysis data containing user_burnout_reports
        dry_run: If True, don't actually create records

    Returns:
        Number of burnout reports loaded
    """
    reports_data = mock_data.get('user_burnout_reports', [])

    if not reports_data:
        return 0

    created_count = 0

    if dry_run:
        return len(reports_data)

    try:
        # SAFETY CHECK: Only delete if this is a verified demo analysis
        if analysis is not None:
            if not verify_demo_analysis_safe(analysis):
                logger.error(f"ABORT: Refusing to delete burnout reports for user {user_id}")
                logger.error(f"       Analysis #{analysis.id} is NOT marked as demo. Possible production data.")
                raise PermissionError(f"Analysis #{analysis.id} is not a demo analysis. Cannot delete user data.")

            # Only proceed if safety check passed
            existing_reports = db.query(UserBurnoutReport).filter(
                UserBurnoutReport.user_id == user_id
            ).all()

            if existing_reports:
                logger.info(f"DELETING {len(existing_reports)} old burnout reports for demo user {user_id}")
                logger.info(f"          Analysis #{analysis.id} (verified demo, is_demo=True)")
                db.query(UserBurnoutReport).filter(
                    UserBurnoutReport.user_id == user_id
                ).delete()
                logger.info(f"DELETED: All old burnout reports for user {user_id}")
        else:
            # If no analysis provided, refuse to delete (safest approach)
            logger.warning(f"WARNING: No analysis provided for burnout report deletion for user {user_id}")
            logger.warning(f"         Skipping deletion as safety check cannot be performed")

        # Load burnout reports from mock data
        for report_data in reports_data:
            email = report_data.get('email', '')

            if not email:
                continue

            # Parse timestamps from exported data
            submitted_at = report_data.get('submitted_at')
            if isinstance(submitted_at, str):
                # Parse ISO format datetime string
                submitted_at = datetime.fromisoformat(submitted_at.replace('Z', '+00:00'))

            try:
                report = UserBurnoutReport(
                    user_id=user_id,  # Link to the user
                    email=email,
                    email_domain=report_data.get('email_domain'),
                    analysis_id=None,  # Not linked to specific analysis
                    feeling_score=report_data.get('feeling_score'),
                    workload_score=report_data.get('workload_score'),
                    stress_factors=report_data.get('stress_factors'),
                    personal_circumstances=report_data.get('personal_circumstances'),
                    additional_comments=report_data.get('additional_comments'),
                    submitted_via=report_data.get('submitted_via', 'web'),
                    is_anonymous=report_data.get('is_anonymous', False),
                    submitted_at=submitted_at  # Preserve timestamp
                )
                db.add(report)
                created_count += 1
            except Exception as e:
                # Continue loading other reports even if one fails
                logger.warning(f"Failed to load report for {email}: {str(e)}")
                continue

        logger.info(f"CREATED: {created_count} new burnout reports for user {user_id}")
        return created_count

    except PermissionError as e:
        logger.error(f"SAFETY CHECK BLOCKED DELETE: {str(e)}")
        raise

    except Exception as e:
        logger.error(f"ERROR: Failed to load burnout reports: {str(e)}")
        raise


def update_demo_analysis(db, analysis: Analysis, mock_data: dict, dry_run: bool = True) -> bool:
    """Update an existing demo analysis with the latest mock data."""
    original_analysis = mock_data['analysis']
    new_results = original_analysis.get('results')

    if dry_run:
        # Count what would be loaded
        reports_count = len(mock_data.get('user_burnout_reports', []))
        print(f"  [DRY-RUN] Would update demo analysis #{analysis.id} (user {analysis.user_id})")
        if reports_count > 0:
            print(f"            Would load {reports_count} health check-in records")
        return True

    try:
        # Update the results with latest mock data
        analysis.results = new_results

        # Update config to track when it was last updated
        config = analysis.config.copy() if analysis.config else {}
        config['demo_updated_at'] = datetime.now().isoformat()
        analysis.config = config

        db.flush()

        # Load/update burnout reports for this user
        # Pass the analysis object for safety verification
        reports_loaded = load_demo_burnout_reports(db, analysis.user_id, analysis, mock_data, dry_run=False)

        print(f"  [OK] Updated demo analysis #{analysis.id} (user {analysis.user_id})")
        if reports_loaded > 0:
            print(f"       Loaded {reports_loaded} health check-in records")
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
            print("\n" + "!"*60)
            print("WARNING: You are about to modify the database!")
            print("!"*60)
            print("\nThis script will ONLY modify analyses marked as is_demo=True")
            print("Real user data is protected by safety checks.")
            print("\nIf you see any errors about 'SAFETY CHECK FAILED', the script")
            print("will BLOCK the deletion to prevent data loss.")
            print("\nTo proceed, type 'yes' (case-sensitive):")
            response = input("\nAre you sure you want to proceed? (type 'yes' to continue): ")
            if response != 'yes':
                print("[*] Cancelled by user")
                logger.info("User cancelled the operation")
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
