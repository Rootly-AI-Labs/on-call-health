"""
Script to diagnose Slack workspace mapping issues.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from app.models import get_db, SlackWorkspaceMapping, User, SlackIntegration
from sqlalchemy.orm import Session

def main():
    db = next(get_db())

    print("=" * 60)
    print("SLACK WORKSPACE MAPPING DIAGNOSTICS")
    print("=" * 60)

    # Check workspace mappings
    mappings = db.query(SlackWorkspaceMapping).all()
    print(f"\n📊 Total workspace mappings: {len(mappings)}")

    if mappings:
        for m in mappings:
            print(f"\n  🏢 Workspace: {m.workspace_name}")
            print(f"     ID: {m.workspace_id}")
            print(f"     Organization ID: {m.organization_id}")
            print(f"     Owner User ID: {m.owner_user_id}")
            print(f"     Status: {m.status}")
            print(f"     Created: {m.created_at}")
    else:
        print("  ❌ No workspace mappings found!")
        print("\n  This explains why the /burnout-survey command shows:")
        print('  "⚠️ This Slack workspace is not registered with any organization"')

    # Check Slack integrations
    print(f"\n{'=' * 60}")
    slack_integrations = db.query(SlackIntegration).all()
    print(f"📱 Total Slack integrations: {len(slack_integrations)}")

    if slack_integrations:
        for si in slack_integrations:
            print(f"\n  User ID: {si.user_id}")
            print(f"  Workspace ID: {si.workspace_id}")
            print(f"  Token Source: {si.token_source}")
            print(f"  Connected At: {si.connected_at}")

    # Check users
    print(f"\n{'=' * 60}")
    users = db.query(User).all()
    print(f"👥 Total users: {len(users)}")

    for u in users:
        print(f"\n  Email: {u.email}")
        print(f"  ID: {u.id}")
        print(f"  Organization ID: {u.organization_id}")

    # Diagnosis
    print(f"\n{'=' * 60}")
    print("🔍 DIAGNOSIS:")
    print("=" * 60)

    if not mappings:
        print("\n❌ ISSUE: No SlackWorkspaceMapping records exist")
        print("\n📝 CAUSE: The OAuth callback likely failed to create the mapping because:")
        print("   1. No state parameter was passed with organization info")
        print("   2. The organization_id was None, so mapping creation might have failed")
        print("   3. Or the OAuth callback never completed successfully")

        print("\n💡 SOLUTIONS:")
        print("\n   Option 1: Manual Database Insert")
        print("   Run this SQL to create the mapping:")
        if slack_integrations and users:
            si = slack_integrations[0]
            u = users[0]
            print(f"""
   INSERT INTO slack_workspace_mappings
   (workspace_id, workspace_name, organization_id, owner_user_id, status, created_at, updated_at)
   VALUES
   ('{si.workspace_id}', 'Your Workspace', {u.organization_id or 'NULL'}, {u.id}, 'active', NOW(), NOW());
            """)

        print("\n   Option 2: Fix OAuth Flow")
        print("   Add state parameter to Slack OAuth URL with organization info")

        print("\n   Option 3: Reconnect Slack")
        print("   Disconnect and reconnect Slack integration from the frontend")
    else:
        print("\n✅ Workspace mappings exist!")

        # Check if the mapping has proper organization
        has_org = any(m.organization_id is not None for m in mappings)
        if not has_org:
            print("⚠️  WARNING: Mappings exist but have NULL organization_id")
            print("   The /burnout-survey command checks for organization_id")
        else:
            print("✅ Mappings have organization_id set properly")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()