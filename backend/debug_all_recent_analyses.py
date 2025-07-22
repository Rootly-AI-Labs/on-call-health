#!/usr/bin/env python3
"""
Debug recent analyses to find one with Slack data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from sqlalchemy import text
import json

def debug_recent_analyses():
    print("🔍 Checking recent analyses for Slack data...\n")
    
    try:
        with SessionLocal() as db:
            # Get several recent completed analyses
            result = db.execute(text("""
                SELECT id, results, created_at, config
                FROM analyses 
                WHERE status = 'completed' 
                AND results IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 5
            """)).fetchall()
            
            if not result:
                print("❌ No completed analyses found")
                return
            
            for analysis in result:
                analysis_id = analysis[0]
                results_json = analysis[1]
                created_at = analysis[2]
                config_json = analysis[3]
                
                print(f"📊 Analysis ID: {analysis_id} (created: {created_at})")
                
                # Check config to see if Slack was requested
                if config_json:
                    try:
                        config = json.loads(config_json)
                        include_slack = config.get('include_slack', False)
                        print(f"  Config include_slack: {include_slack}")
                    except:
                        print(f"  Config (raw): {config_json}")
                
                try:
                    results = json.loads(results_json)
                    
                    # Check if there's any data at all
                    members = results.get('organization_members', [])
                    team_summary = results.get('team_summary', {})
                    
                    print(f"  Members: {len(members)}")
                    print(f"  Team Summary Keys: {list(team_summary.keys())}")
                    
                    # Look for any Slack data
                    has_slack_data = False
                    
                    # Check team summary
                    slack_team = team_summary.get('slack_activity', {})
                    if slack_team:
                        print(f"  ✅ Team Slack Data: {list(slack_team.keys())}")
                        has_slack_data = True
                    
                    # Check individual members
                    for member in members:
                        slack_member = member.get('slack_activity', {})
                        if slack_member and slack_member != {}:
                            print(f"  ✅ Member Slack Data: {member.get('user_name')} - {list(slack_member.keys())}")
                            has_slack_data = True
                            break
                    
                    if not has_slack_data:
                        print(f"  ❌ No Slack data found")
                    
                    print()
                    
                except json.JSONDecodeError as e:
                    print(f"  ❌ Error parsing JSON: {e}")
                    print()
                
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    debug_recent_analyses()