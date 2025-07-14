#!/usr/bin/env python3
"""
Script to check current Slack integration scopes and guide re-authorization.
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add the backend directory to the path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.models import get_db, SlackIntegration
from app.api.endpoints.slack import decrypt_token
import httpx

async def check_slack_scopes():
    """Check what scopes the current Slack integration has."""
    
    print("🔍 Checking Slack Integration Scopes...")
    print("=" * 50)
    
    # Get database connection
    db = next(get_db())
    
    # Find Slack integration (assuming user ID 2 based on logs)
    integration = db.query(SlackIntegration).filter(
        SlackIntegration.user_id == 2
    ).first()
    
    if not integration:
        print("❌ No Slack integration found!")
        return False
    
    print(f"✅ Found Slack integration:")
    print(f"   - Token source: {integration.token_source}")
    print(f"   - Workspace ID: {integration.workspace_id}")
    print(f"   - Created: {integration.created_at}")
    print()
    
    try:
        # Decrypt token
        access_token = decrypt_token(integration.slack_token)
        print(f"🔑 Token preview: {access_token[:20]}...")
        print()
        
        # Test scopes
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        scope_tests = {
            "conversations.list": "❌",
            "conversations.history": "❌", 
            "users.conversations": "❌",
            "users.list": "❌",
            "auth.test": "❌"
        }
        
        async with httpx.AsyncClient() as client:
            # Test auth.test
            try:
                response = await client.get("https://slack.com/api/auth.test", headers=headers)
                result = response.json()
                if result.get("ok"):
                    scope_tests["auth.test"] = "✅"
                    user_id = result.get("user_id")
                    print(f"👤 User ID: {user_id}")
                    print(f"🏢 Team: {result.get('team')}")
                else:
                    scope_tests["auth.test"] = f"❌ {result.get('error', 'Unknown')}"
            except Exception as e:
                scope_tests["auth.test"] = f"❌ Exception: {str(e)}"
            
            # Test conversations.list
            try:
                response = await client.get("https://slack.com/api/conversations.list", headers=headers, params={"limit": 1})
                result = response.json()
                if result.get("ok"):
                    scope_tests["conversations.list"] = "✅"
                    channels = result.get("channels", [])
                    print(f"📋 Found {len(channels)} channels")
                    
                    # Test conversations.history if we have channels
                    if channels:
                        channel_id = channels[0]["id"]
                        try:
                            response = await client.get("https://slack.com/api/conversations.history", headers=headers, params={"channel": channel_id, "limit": 1})
                            result = response.json()
                            if result.get("ok"):
                                scope_tests["conversations.history"] = "✅"
                                messages = result.get("messages", [])
                                print(f"💬 Can read message history: {len(messages)} messages in sample")
                            else:
                                scope_tests["conversations.history"] = f"❌ {result.get('error', 'Unknown')}"
                        except Exception as e:
                            scope_tests["conversations.history"] = f"❌ Exception: {str(e)}"
                else:
                    scope_tests["conversations.list"] = f"❌ {result.get('error', 'Unknown')}"
            except Exception as e:
                scope_tests["conversations.list"] = f"❌ Exception: {str(e)}"
            
            # Test users.conversations
            if user_id:
                try:
                    response = await client.get("https://slack.com/api/users.conversations", headers=headers, params={"user": user_id, "limit": 1})
                    result = response.json()
                    if result.get("ok"):
                        scope_tests["users.conversations"] = "✅"
                        user_channels = result.get("channels", [])
                        print(f"👥 User is in {len(user_channels)} channels")
                    else:
                        scope_tests["users.conversations"] = f"❌ {result.get('error', 'Unknown')}"
                except Exception as e:
                    scope_tests["users.conversations"] = f"❌ Exception: {str(e)}"
            
            # Test users.list
            try:
                response = await client.get("https://slack.com/api/users.list", headers=headers, params={"limit": 1})
                result = response.json()
                if result.get("ok"):
                    scope_tests["users.list"] = "✅"
                else:
                    scope_tests["users.list"] = f"❌ {result.get('error', 'Unknown')}"
            except Exception as e:
                scope_tests["users.list"] = f"❌ Exception: {str(e)}"
        
        print()
        print("🧪 Scope Test Results:")
        print("=" * 30)
        for scope, result in scope_tests.items():
            print(f"   {scope}: {result}")
        
        # Check if we have the required scopes
        required_scopes = ["conversations.list", "conversations.history", "users.conversations"]
        has_all_required = all(scope_tests[scope] == "✅" for scope in required_scopes)
        
        print()
        if has_all_required:
            print("✅ All required scopes are available!")
            print("   Your Slack integration should work correctly for burnout analysis.")
            return True
        else:
            print("❌ Missing required scopes for burnout analysis!")
            print("   Required scopes:")
            for scope in required_scopes:
                status = scope_tests.get(scope, "❌")
                print(f"   - {scope}: {status}")
            print()
            print("🔄 Re-authorization needed!")
            print_reauth_guide()
            return False
            
    except Exception as e:
        print(f"❌ Error checking scopes: {str(e)}")
        return False

def print_reauth_guide():
    """Print guide for re-authorization."""
    print()
    print("📖 Re-authorization Guide:")
    print("=" * 30)
    print("1. Go to http://localhost:3000/integrations")
    print("2. Find your Slack integration")
    print("3. Click 'Disconnect' to remove the current integration")
    print("4. Set up a new Slack integration with proper OAuth scopes")
    print()
    print("Required Slack App Scopes:")
    print("- channels:history")
    print("- groups:history") 
    print("- users:read")
    print("- conversations.history")
    print("- channels:read")
    print("- groups:read")
    print("- users:read.email")
    print()
    print("💡 If you're using a manual token, make sure your Slack app")
    print("   has all these scopes enabled in the OAuth & Permissions page.")

if __name__ == "__main__":
    try:
        result = asyncio.run(check_slack_scopes())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)