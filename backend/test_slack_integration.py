#!/usr/bin/env python3
"""
Test Slack integration and data collection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from sqlalchemy import text
import json

def test_slack_integration_setup():
    print("🔍 Testing Slack integration setup...\n")
    
    try:
        with SessionLocal() as db:
            # Check Slack integrations
            result = db.execute(text("""
                SELECT id, user_id, slack_user_id, workspace_id, created_at,
                       CASE WHEN slack_token IS NOT NULL THEN 'Has Token' ELSE 'No Token' END as token_status,
                       CASE WHEN webhook_url IS NOT NULL THEN 'Has Webhook' ELSE 'No Webhook' END as webhook_status
                FROM slack_integrations
            """)).fetchall()
            
            if not result:
                print("❌ No Slack integrations found in database")
                return False
            
            print(f"📊 Found {len(result)} Slack integration(s):")
            for integration in result:
                print(f"  - ID: {integration[0]}, User: {integration[1]}")
                print(f"    Slack User ID: {integration[2]}")
                print(f"    Workspace ID: {integration[3]}")
                print(f"    Created: {integration[4]}")
                print(f"    Token: {integration[5]}")
                print(f"    Webhook: {integration[6]}")
                print()
            
            return True
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_slack_api_connection():
    print("🔍 Testing Slack API connection...\n")
    
    try:
        # Test if we can reach Slack API
        from app.services.slack_collector import SlackCollector
        
        # Get a Slack integration to test with
        with SessionLocal() as db:
            result = db.execute(text("""
                SELECT slack_token FROM slack_integrations LIMIT 1
            """)).fetchone()
            
            if not result:
                print("❌ No Slack token found")
                return False
            
            # Initialize collector (this will decrypt the token)
            collector = SlackCollector()
            print("✅ SlackCollector initialized successfully")
            
            # Note: We can't test the actual API call without decrypting the token
            # but we can check if the collector can be instantiated
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing Slack collector: {e}")
        return False

def test_slack_data_in_analysis():
    print("🔍 Testing if Slack data should be included in analysis...\n")
    
    try:
        # Check the burnout analyzer to see if it's trying to include Slack
        from app.services.burnout_analyzer import BurnoutAnalyzer
        
        # Look at recent analysis request to see if Slack was requested
        with SessionLocal() as db:
            result = db.execute(text("""
                SELECT id, config, error_message
                FROM analyses 
                WHERE status IN ('completed', 'failed')
                ORDER BY created_at DESC 
                LIMIT 3
            """)).fetchall()
            
            if not result:
                print("❌ No recent analyses found")
                return
            
            for analysis in result:
                analysis_id = analysis[0]
                config_str = analysis[1]
                error_msg = analysis[2]
                
                print(f"📊 Analysis ID: {analysis_id}")
                
                if config_str:
                    try:
                        config = json.loads(config_str)
                        include_slack = config.get('include_slack', False)
                        print(f"  Include Slack: {include_slack}")
                    except:
                        print(f"  Config: {config_str}")
                else:
                    print("  No config found")
                
                if error_msg:
                    print(f"  Error: {error_msg}")
                
                print()
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Test Slack integration setup
    has_integration = test_slack_integration_setup()
    
    if has_integration:
        print("=" * 50)
        test_slack_api_connection()
        
        print("=" * 50)
        test_slack_data_in_analysis()
    else:
        print("⚠️ No Slack integration found - this explains why there's no sentiment data")