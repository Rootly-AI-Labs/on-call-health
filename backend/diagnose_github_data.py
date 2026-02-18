#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Data Diagnostic Script
Diagnose GitHub data issues across environments (localhost, Railway dev/prod, etc.)

Usage:
  # Default localhost (interactive email prompt)
  python diagnose_github_data.py

  # Specify email
  python diagnose_github_data.py --email user@example.com

  # Deployed database (secure - uses DATABASE_URL from environment)
  DATABASE_URL=postgresql://... python diagnose_github_data.py --deployed --email user@example.com

  # Quick debugging (command-line URL)
  python diagnose_github_data.py --database-url "postgresql://..." --email user@example.com

  # Full help
  python diagnose_github_data.py --help
"""

import sys
import os
import argparse
from urllib.parse import urlparse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONFIGURATION FUNCTIONS
# ============================================================================

def parse_arguments():
    """Parse command-line arguments for database URL and user email."""
    parser = argparse.ArgumentParser(
        description="GitHub Data Diagnostic Script - Diagnose GitHub data issues across environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default localhost (backwards compatible)
  python diagnose_github_data.py --email user@example.com

  # Interactive mode (prompts for email)
  python diagnose_github_data.py

  # Use DATABASE_URL from environment (secure for deployed)
  DATABASE_URL=postgresql://user:pass@host:5432/db python diagnose_github_data.py --deployed --email user@example.com

  # Quick debugging with command-line URL
  python diagnose_github_data.py --database-url "postgresql://user:pass@host:5432/db" --email user@example.com

  # Compare localhost vs deployed
  python diagnose_github_data.py --email user@example.com > localhost.txt
  DATABASE_URL=$DEPLOYED_URL python diagnose_github_data.py --deployed --email user@example.com > deployed.txt
  diff localhost.txt deployed.txt

Security Notes:
  - Prefer DATABASE_URL environment variable over --database-url (not in command history)
  - Passwords are automatically masked in output (shown as ****)
  - Use --deployed flag to explicitly require DATABASE_URL from environment
        """
    )

    parser.add_argument(
        '--database-url',
        type=str,
        help='Database URL (e.g., postgresql://user:pass@host:5432/db). Overrides DATABASE_URL env var.'
    )

    parser.add_argument(
        '--email',
        type=str,
        help='User email address to diagnose. Can also set USER_EMAIL env var.'
    )

    parser.add_argument(
        '--deployed',
        action='store_true',
        help='Use DATABASE_URL from environment (required for deployed environments). More secure than --database-url.'
    )

    return parser.parse_args()


def get_database_url(args):
    """
    Resolve database URL from arguments or environment.

    Priority order:
    1. --database-url command-line argument
    2. --deployed flag → requires DATABASE_URL environment variable
    3. DATABASE_URL environment variable
    4. Default to localhost (backwards compatibility)
    """
    # Priority 1: Command-line argument
    if args.database_url:
        print("ℹ️  Using DATABASE_URL from --database-url argument")
        return args.database_url

    # Priority 2: --deployed flag requires environment variable
    if args.deployed:
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            print("❌ ERROR: --deployed flag requires DATABASE_URL environment variable")
            print("   Set it with: DATABASE_URL=postgresql://... python diagnose_github_data.py --deployed")
            sys.exit(1)
        print("ℹ️  Using DATABASE_URL from environment (--deployed mode)")
        return db_url

    # Priority 3: Environment variable
    db_url = os.environ.get('DATABASE_URL')
    if db_url:
        print("ℹ️  Using DATABASE_URL from environment")
        return db_url

    # Priority 4: Default localhost (backwards compatibility)
    print("ℹ️  Using default localhost database (no DATABASE_URL found)")
    return "postgresql://postgres:1234@localhost:5432/burnout_detector"


def get_user_email(args):
    """
    Resolve user email from arguments, environment, or interactive prompt.

    Priority order:
    1. --email command-line argument
    2. USER_EMAIL environment variable
    3. Interactive prompt
    """
    # Priority 1: Command-line argument
    if args.email:
        return args.email

    # Priority 2: Environment variable
    email = os.environ.get('USER_EMAIL')
    if email:
        print("ℹ️  Using USER_EMAIL from environment")
        return email

    # Priority 3: Interactive prompt
    print("\nℹ️  No email provided via --email or USER_EMAIL environment variable")
    email = input("Enter the email address to diagnose: ").strip()
    if not email:
        print("❌ ERROR: Email address is required")
        sys.exit(1)
    return email


def validate_database_url(url):
    """
    Validate database URL format.

    Returns True if valid, False otherwise.
    """
    try:
        parsed = urlparse(url)

        # Check scheme
        if parsed.scheme not in ['postgresql', 'postgres']:
            print(f"❌ ERROR: Invalid database URL scheme: {parsed.scheme}")
            print(f"   Expected: postgresql:// or postgres://")
            return False

        # Check host
        if not parsed.hostname:
            print(f"❌ ERROR: Database URL missing hostname")
            return False

        # Check database name
        if not parsed.path or parsed.path == '/':
            print(f"❌ ERROR: Database URL missing database name")
            return False

        return True
    except Exception as e:
        print(f"❌ ERROR: Invalid database URL format: {e}")
        return False


def get_safe_database_display(url):
    """
    Return database URL with password masked for safe display.

    Example: postgresql://user:****@host:5432/db
    """
    try:
        parsed = urlparse(url)

        # Build safe URL with masked password
        safe_url = f"{parsed.scheme}://"

        if parsed.username:
            safe_url += parsed.username
            if parsed.password:
                safe_url += ":****"
            safe_url += "@"

        safe_url += parsed.hostname or ""

        if parsed.port:
            safe_url += f":{parsed.port}"

        safe_url += parsed.path or ""

        return safe_url
    except:
        # Fallback: just hide everything after @ if present
        if '@' in url:
            return url.split('@')[1]
        return url


# ============================================================================
# PARSE ARGUMENTS AND CONFIGURATION
# ============================================================================
args = parse_arguments()
DATABASE_URL = get_database_url(args)
USER_EMAIL = get_user_email(args)

# Validate database URL
if not validate_database_url(DATABASE_URL):
    print("\n💡 Troubleshooting:")
    print("   1. Check URL format: postgresql://user:password@host:port/database")
    print("   2. Ensure all components are present (host, database name)")
    print("   3. Use quotes around URL if it contains special characters")
    sys.exit(1)

# ============================================================================
# Connect to Database
# ============================================================================
print("=" * 80)
print("🔍 GitHub Data Diagnostic Script")
print("=" * 80)
print(f"\n📍 Database: {get_safe_database_display(DATABASE_URL)}")
print(f"👤 User Email: {USER_EMAIL}")
print(f"🔧 Mode: {'Deployed' if args.deployed else 'Local/Custom'}\n")

try:
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    # Test connection with a simple query
    db.execute(text("SELECT 1")).fetchone()
    print("✅ Database connection successful\n")
except Exception as e:
    print(f"❌ Failed to connect to database")
    print(f"   Error: {e}")
    print(f"\n💡 Troubleshooting:")
    print(f"   1. Check database URL: {get_safe_database_display(DATABASE_URL)}")
    print(f"   2. Verify database is running and accessible")
    print(f"   3. Check credentials and permissions")
    print(f"   4. Ensure network connectivity (firewall, VPN, etc.)")
    if args.deployed:
        print(f"   5. For Railway/deployed: verify DATABASE_URL environment variable is correct")
    else:
        print(f"   5. For localhost: ensure PostgreSQL is running on port 5432")
    sys.exit(1)

# ============================================================================
# 1. CHECK: User Account and Organization
# ============================================================================
print("=" * 80)
print("1️⃣  USER ACCOUNT")
print("=" * 80)

try:
    result = db.execute(text("""
        SELECT id, email, organization_id, created_at
        FROM users
        WHERE email = :email
        LIMIT 1
    """), {"email": USER_EMAIL}).fetchone()

    if result:
        user_id = result[0]
        org_id = result[2]
        print(f"✅ User Found:")
        print(f"   - User ID: {result[0]}")
        print(f"   - Email: {result[1]}")
        print(f"   - Organization ID: {result[2] or 'NULL (not part of org)'}")
        print(f"   - Created: {result[3]}")
    else:
        print(f"❌ User not found with email: {USER_EMAIL}")
        sys.exit(1)
except Exception as e:
    print(f"❌ Error querying users: {e}")
    sys.exit(1)

# ============================================================================
# 2. CHECK: GitHub Integration Status
# ============================================================================
print("\n" + "=" * 80)
print("2️⃣  GITHUB INTEGRATION STATUS")
print("=" * 80)

try:
    result = db.execute(text("""
        SELECT id, user_id, github_username, github_token IS NOT NULL as has_token,
               token_source, created_at, updated_at
        FROM github_integrations
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 1
    """), {"user_id": user_id}).fetchone()

    if result:
        github_integration_id = result[0]
        has_token = result[3]
        print(f"✅ GitHub Integration Found:")
        print(f"   - Integration ID: {result[0]}")
        print(f"   - GitHub Username: {result[2]}")
        print(f"   - Has Token: {result[3]}")
        print(f"   - Token Source: {result[4]}")
        print(f"   - Created: {result[5]}")
        print(f"   - Updated: {result[6]}")

        if not has_token:
            print(f"\n⚠️  WARNING: GitHub integration has NO TOKEN!")
    else:
        print(f"❌ No GitHub integration found for user {user_id}")
        print(f"   This means GitHub was never connected for this user.")
except Exception as e:
    print(f"❌ Error querying github_integrations: {e}")
    db.rollback()  # Rollback failed transaction

# ============================================================================
# 3. CHECK: UserCorrelation Records (GitHub)
# ============================================================================
print("\n" + "=" * 80)
print("3️⃣  USER CORRELATIONS (GitHub Mappings)")
print("=" * 80)

try:
    results = db.execute(text("""
        SELECT id, email, github_username, organization_id, user_id, created_at
        FROM user_correlations
        WHERE github_username IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 15
    """)).fetchall()

    if results:
        print(f"✅ Found {len(results)} UserCorrelation records with GitHub usernames:")

        # Group by organization_id
        by_org = {}
        for row in results:
            org_key = row[3] or "NULL"
            if org_key not in by_org:
                by_org[org_key] = []
            by_org[org_key].append(row)

        for org_key, records in by_org.items():
            print(f"\n   📁 Organization ID: {org_key}")
            for row in records[:5]:  # Show max 5 per org
                print(f"      - {row[1]:30} → {row[2]:20} (created: {row[5]})")
            if len(records) > 5:
                print(f"      ... and {len(records) - 5} more")

        # Check if any match our user's organization
        user_org_records = [r for r in results if r[3] == org_id or (r[3] is None and org_id is None)]
        if user_org_records:
            print(f"\n   ✅ {len(user_org_records)} records match user's organization (org_id={org_id})")
        else:
            print(f"\n   ⚠️  WARNING: NO records match user's organization_id={org_id}")
            print(f"      This could explain why GitHub data isn't showing!")
    else:
        print(f"❌ No UserCorrelation records found with github_username")
        print(f"   This means 'Sync Members' might not have synced GitHub usernames.")
except Exception as e:
    print(f"❌ Error querying user_correlations: {e}")
    db.rollback()

# ============================================================================
# 4. CHECK: IntegrationMapping Records (GitHub)
# ============================================================================
print("\n" + "=" * 80)
print("4️⃣  INTEGRATION MAPPINGS (GitHub)")
print("=" * 80)

try:
    results = db.execute(text("""
        SELECT
            id,
            analysis_id,
            source_identifier,
            target_identifier,
            mapping_successful,
            data_points_count,
            created_at
        FROM integration_mappings
        WHERE target_platform = 'github'
          AND mapping_successful = true
        ORDER BY created_at DESC
        LIMIT 15
    """)).fetchall()

    if results:
        print(f"✅ Found {len(results)} successful GitHub IntegrationMapping records:")

        # Group by analysis_id
        by_analysis = {}
        for row in results:
            analysis_key = row[1] or "NULL"
            if analysis_key not in by_analysis:
                by_analysis[analysis_key] = []
            by_analysis[analysis_key].append(row)

        for analysis_key, records in by_analysis.items():
            print(f"\n   📊 Analysis ID: {analysis_key}")
            for row in records[:5]:
                print(f"      - {row[2]:30} → {row[3]:20} (data_points: {row[5]}, created: {row[6]})")
            if len(records) > 5:
                print(f"      ... and {len(records) - 5} more")
    else:
        print(f"❌ No successful GitHub IntegrationMapping records found")
        print(f"   This means GitHub mapping failed during analysis.")
except Exception as e:
    print(f"❌ Error querying integration_mappings: {e}")
    db.rollback()

# ============================================================================
# 5. CHECK: Recent Analyses
# ============================================================================
print("\n" + "=" * 80)
print("5️⃣  RECENT ANALYSES")
print("=" * 80)

try:
    results = db.execute(text("""
        SELECT
            id,
            organization_id,
            status,
            platform,
            time_range,
            created_at,
            (results IS NOT NULL) as has_results
        FROM analyses
        WHERE user_id = :user_id
        ORDER BY created_at DESC
        LIMIT 5
    """), {"user_id": user_id}).fetchall()

    if results:
        print(f"✅ Found {len(results)} recent analyses:")
        for row in results:
            print(f"\n   📊 Analysis ID: {row[0]}")
            print(f"      - Organization ID: {row[1] or 'NULL'}")
            print(f"      - Status: {row[2]}")
            print(f"      - Platform: {row[3]}")
            print(f"      - Time Range: {row[4]} days")
            print(f"      - Created: {row[5]}")
            print(f"      - Has Results: {row[6]}")
    else:
        print(f"❌ No analyses found for user {user_id}")
except Exception as e:
    print(f"❌ Error querying analyses: {e}")
    db.rollback()

# ============================================================================
# 6. CHECK: GitHub Data in Most Recent Completed Analysis
# ============================================================================
print("\n" + "=" * 80)
print("6️⃣  GITHUB DATA IN MOST RECENT ANALYSIS")
print("=" * 80)

try:
    result = db.execute(text("""
        SELECT
            id,
            organization_id,
            created_at,
            results
        FROM analyses
        WHERE user_id = :user_id
          AND status = 'completed'
          AND results IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1
    """), {"user_id": user_id}).fetchone()

    if result:
        analysis_id = result[0]
        analysis_org_id = result[1]
        results_json = result[3]

        print(f"✅ Most Recent Completed Analysis:")
        print(f"   - Analysis ID: {analysis_id}")
        print(f"   - Organization ID: {analysis_org_id or 'NULL'}")
        print(f"   - Created: {result[2]}")

        # Parse team_analysis
        if results_json and 'team_analysis' in results_json:
            team_analysis = results_json['team_analysis']
            team_members = team_analysis.get('members', team_analysis.get('team_members', []))

            print(f"\n   📋 Team Members: {len(team_members)} total")

            # Check GitHub data
            members_with_github = 0
            github_sample = []

            for member in team_members[:10]:  # Check first 10
                email = member.get('user_email', 'unknown')
                github_activity = member.get('github_activity')
                has_github = github_activity is not None and github_activity != {}

                if has_github:
                    members_with_github += 1
                    commits = github_activity.get('commits_count', 0)
                    github_username = member.get('github_username') or 'unknown'
                    github_sample.append({
                        'email': email,
                        'commits': commits,
                        'github_username': github_username
                    })

            print(f"   📊 Members with GitHub Data: {members_with_github}/{len(team_members)}")

            if members_with_github > 0:
                print(f"\n   ✅ GitHub data IS present! Sample:")
                for sample in github_sample[:5]:
                    print(f"      - {sample['email']:30} → {sample['github_username']:20} (commits: {sample['commits']})")
            else:
                print(f"\n   ❌ NO GitHub data found in team_members!")
                print(f"      Checking github_insights section...")

            # Check github_insights (this is where the actual GitHub data lives!)
            if 'github_insights' in results_json:
                github_insights = results_json['github_insights']
                total_commits = github_insights.get('total_commits', 0)
                total_prs = github_insights.get('total_pull_requests', 0)
                top_contributors = github_insights.get('top_contributors', [])

                print(f"\n   🔍 GitHub Insights Section:")
                print(f"      - Total Commits: {total_commits}")
                print(f"      - Total PRs: {total_prs}")
                print(f"      - Top Contributors: {len(top_contributors)}")

                if len(top_contributors) > 0:
                    print(f"\n      ✅ TOP CONTRIBUTORS (this is the actual GitHub data!):")
                    for contrib in top_contributors[:5]:
                        name = contrib.get('name', 'unknown')
                        commits = contrib.get('total_commits', 0)
                        prs = contrib.get('total_prs', 0)
                        print(f"         - {name:30} commits={commits:4} PRs={prs:3}")

                    if total_commits > 0:
                        print(f"\n      ✅✅ SUCCESS: GitHub data IS present on this environment!")
                    else:
                        print(f"\n      ⚠️  Top contributors exist but total_commits=0")
                else:
                    print(f"\n      ❌ NO top contributors - GitHub data collection failed!")
            else:
                print(f"\n   ❌ NO github_insights section found in results!")
        else:
            print(f"   ⚠️  No team_analysis found in results")
    else:
        print(f"❌ No completed analyses found for user {user_id}")
except Exception as e:
    print(f"❌ Error checking GitHub data in analysis: {e}")
    db.rollback()

# ============================================================================
# 7. SUMMARY & RECOMMENDATIONS
# ============================================================================
print("\n" + "=" * 80)
print("📋 DIAGNOSTIC SUMMARY")
print("=" * 80)

# Collect findings
findings = []
recommendations = []

# Check organization_id mismatch
if org_id is None:
    findings.append("⚠️  User has NO organization_id (org_id=NULL)")
    recommendations.append("If using multi-tenant mode, assign user to an organization")
else:
    findings.append(f"✅ User has organization_id={org_id}")

# Check UserCorrelation records
try:
    correlation_count = db.execute(text("""
        SELECT COUNT(*) FROM user_correlations
        WHERE github_username IS NOT NULL
        AND (organization_id = :org_id OR (:org_id IS NULL AND organization_id IS NULL))
    """), {"org_id": org_id}).fetchone()[0]

    if correlation_count == 0:
        findings.append(f"❌ NO UserCorrelation records with github_username for org_id={org_id}")
        recommendations.append("Run 'Sync Members' on integrations page to populate GitHub usernames")
    else:
        findings.append(f"✅ {correlation_count} UserCorrelation records with GitHub usernames")
except:
    pass

# Check IntegrationMapping records
try:
    mapping_count = db.execute(text("""
        SELECT COUNT(*) FROM integration_mappings
        WHERE target_platform = 'github'
        AND mapping_successful = true
    """)).fetchone()[0]

    if mapping_count == 0:
        findings.append("❌ NO successful GitHub IntegrationMapping records")
        recommendations.append("GitHub mapping failed - check logs during analysis run")
    else:
        findings.append(f"✅ {mapping_count} successful GitHub IntegrationMapping records")
except:
    pass

print("\n🔍 Findings:")
for finding in findings:
    print(f"   {finding}")

if recommendations:
    print("\n💡 Recommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
else:
    print("\n✅ No obvious issues found. GitHub data collection pipeline appears healthy.")
    print("   If data still not showing, check:")
    print("   1. GitHub token validity and permissions")
    print("   2. Backend logs during analysis run for errors")
    print("   3. Network connectivity to GitHub API from deployed environment")

print("\n" + "=" * 80)
print("✅ Diagnostic Complete!")
print("=" * 80)

# Close connection
db.close()
