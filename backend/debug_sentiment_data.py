#!/usr/bin/env python3
"""
Debug sentiment data structure in analysis results
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from sqlalchemy import text
import json

def debug_sentiment_data():
    print("🔍 Debugging sentiment data structure...\n")
    
    try:
        with SessionLocal() as db:
            # Get the most recent completed analysis
            result = db.execute(text("""
                SELECT id, results, created_at
                FROM analyses 
                WHERE status = 'completed' 
                AND results IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
            """)).fetchone()
            
            if not result:
                print("❌ No completed analyses found")
                return
            
            analysis_id = result[0]
            results_json = result[1]
            created_at = result[2]
            
            print(f"📊 Analysis ID: {analysis_id} (created: {created_at})")
            
            try:
                results = json.loads(results_json)
                
                # Check team summary structure
                team_summary = results.get('team_summary', {})
                print(f"\n📋 Team Summary Keys: {list(team_summary.keys())}")
                
                slack_summary = team_summary.get('slack_activity', {})
                if slack_summary:
                    print(f"\n💬 Slack Team Summary:")
                    print(f"  Keys: {list(slack_summary.keys())}")
                    
                    # Check for sentiment_analysis
                    sentiment_analysis = slack_summary.get('sentiment_analysis', {})
                    if sentiment_analysis:
                        print(f"  Sentiment Analysis: {sentiment_analysis}")
                    else:
                        print(f"  ❌ No 'sentiment_analysis' key found")
                        print(f"  Available data: {slack_summary}")
                else:
                    print(f"\n❌ No slack_activity in team_summary")
                
                # Check individual member data
                members = results.get('organization_members', [])
                print(f"\n👥 Found {len(members)} organization members")
                
                for member in members:
                    name = member.get('user_name', 'Unknown')
                    slack_activity = member.get('slack_activity', {})
                    
                    if slack_activity and slack_activity != {}:
                        print(f"\n👤 {name} - Slack Activity:")
                        print(f"  Keys: {list(slack_activity.keys())}")
                        
                        sentiment_score = slack_activity.get('sentiment_score')
                        if sentiment_score is not None:
                            print(f"  ✅ Sentiment Score: {sentiment_score}")
                        else:
                            print(f"  ❌ No sentiment_score found")
                        
                        print(f"  Messages: {slack_activity.get('messages_sent', 0)}")
                        print(f"  Response Time: {slack_activity.get('avg_response_time_minutes', 0)} min")
                        break
                else:
                    print("\n❌ No members with slack_activity found")
                
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing JSON: {e}")
                
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    debug_sentiment_data()