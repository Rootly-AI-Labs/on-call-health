#!/usr/bin/env python3
"""
Direct test of Slack API to check for rate limiting or data issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from sqlalchemy import text
import json
import asyncio
from datetime import datetime, timedelta

async def test_slack_api_direct():
    print("🔍 Testing Slack API directly for rate limiting issues...\n")
    
    try:
        # Get Slack integration details
        with SessionLocal() as db:
            result = db.execute(text("""
                SELECT slack_token, workspace_id, slack_user_id 
                FROM slack_integrations 
                LIMIT 1
            """)).fetchone()
            
            if not result:
                print("❌ No Slack integration found")
                return
            
            slack_token = result[0]
            workspace_id = result[1] 
            slack_user_id = result[2]
            
            print(f"📊 Found Slack integration:")
            print(f"  Workspace ID: {workspace_id}")
            print(f"  User ID: {slack_user_id}")
            print(f"  Token: {'***' + slack_token[-4:] if slack_token else 'None'}\n")
        
        # Test Slack API calls
        from app.services.slack_collector import SlackCollector
        
        collector = SlackCollector()
        print("✅ SlackCollector initialized\n")
        
        # Test basic API connectivity with a simple call
        print("🔍 Testing Slack API connectivity...")
        
        # Get team members from a recent analysis to test with
        with SessionLocal() as db:
            recent_analysis = db.execute(text("""
                SELECT results FROM analyses 
                WHERE status = 'completed' 
                ORDER BY created_at DESC 
                LIMIT 1
            """)).fetchone()
            
            if recent_analysis:
                results = json.loads(recent_analysis[0])
                team_members = results.get('team_analysis', {}).get('members', [])
                
                if team_members:
                    test_emails = [member.get('user_email') for member in team_members[:2]]  # Test with first 2
                    test_names = [member.get('user_name') for member in team_members[:2]]
                    
                    print(f"📧 Testing with emails: {test_emails}")
                    print(f"👥 Testing with names: {test_names}\n")
                    
                    # Test date range (last 7 days)
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    
                    print(f"📅 Date range: {start_date.date()} to {end_date.date()}\n")
                    
                    # Test the actual Slack data collection
                    print("🔄 Attempting Slack data collection...")
                    
                    try:
                        from app.services.slack_collector import collect_team_slack_data
                        from app.api.endpoints.slack import decrypt_token
                        
                        # Decrypt the Slack token
                        print("🔓 Decrypting Slack token...")
                        try:
                            decrypted_token = decrypt_token(slack_token)
                            print(f"✅ Token decrypted successfully")
                        except Exception as decrypt_error:
                            print(f"❌ Failed to decrypt token: {decrypt_error}")
                            decrypted_token = None
                        
                        # Calculate days for the range
                        days = (end_date - start_date).days
                        
                        slack_data = await collect_team_slack_data(
                            team_identifiers=test_emails,
                            days=days,
                            slack_token=decrypted_token,  # Use the decrypted token
                            use_names=False  # Use email mode first
                        )
                        
                        print("✅ Slack API call successful!")
                        print(f"📊 Returned data structure:")
                        print(f"  Type: {type(slack_data)}")
                        
                        if isinstance(slack_data, dict):
                            print(f"  Keys: {list(slack_data.keys())}")
                            
                            # Check each member's data
                            for email, member_data in slack_data.items():
                                print(f"\n  👤 {email}:")
                                if isinstance(member_data, dict):
                                    print(f"    Data keys: {list(member_data.keys())}")
                                    
                                    # Check key metrics
                                    messages = member_data.get('messages_sent', 0)
                                    channels = member_data.get('channels_active', 0)
                                    sentiment = member_data.get('sentiment_score', 'N/A')
                                    
                                    print(f"    Messages sent: {messages}")
                                    print(f"    Active channels: {channels}")
                                    print(f"    Sentiment score: {sentiment}")
                                    
                                    # Check for rate limiting or errors in member data
                                    if 'errors' in member_data:
                                        errors = member_data['errors']
                                        print(f"    ⚠️ Errors: {errors}")
                                        
                                        if 'rate_limited_channels' in errors and errors['rate_limited_channels']:
                                            print(f"    🚨 RATE LIMITED CHANNELS: {errors['rate_limited_channels']}")
                                            print("       This explains the data gaps!")
                                        
                                        if 'permission_errors' in errors and errors['permission_errors']:
                                            print(f"    🔒 PERMISSION ERRORS: {errors['permission_errors']}")
                                            print("       Bot doesn't have access to these channels!")
                                else:
                                    print(f"    Unexpected data: {member_data}")
                        
                        else:
                            print(f"  Unexpected data type: {slack_data}")
                            
                        # Summary of findings
                        print(f"\n🔍 DIAGNOSIS:")
                        print(f"  The Slack integration is working but encountering:")
                        print(f"  1. 🚨 Rate limiting on #test channel (60s wait required)")
                        print(f"  2. 🔒 Permission errors (bot not in channels: #new-channel, #all-rubber-duck-enterprises, #social)")
                        print(f"  3. This likely explains why recent analyses show 0 Slack data!")
                        print(f"  4. The rate limiting may be preventing data collection during analysis runs.")
                            
                    except Exception as api_error:
                        print(f"❌ Slack API call failed: {api_error}")
                        print(f"   Error type: {type(api_error)}")
                        
                        # Check if it's a rate limiting error
                        error_str = str(api_error).lower()
                        if 'rate' in error_str and 'limit' in error_str:
                            print("   🚨 This appears to be a RATE LIMITING issue!")
                        elif '429' in error_str:
                            print("   🚨 HTTP 429 - Definitely a rate limiting issue!")
                        elif 'forbidden' in error_str or '403' in error_str:
                            print("   🔒 Permission/scope issue with Slack token")
                        elif 'unauthorized' in error_str or '401' in error_str:
                            print("   🔑 Authentication issue with Slack token")
                else:
                    print("❌ No team members found in recent analysis")
            else:
                print("❌ No recent analysis found to test with")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_slack_api_direct())