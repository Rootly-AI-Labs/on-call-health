#!/usr/bin/env python3
"""
Check analysis ID 115 for AI insights
"""
import sqlite3
import json
from datetime import datetime

def check_analysis(analysis_id):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get the analysis
    cursor.execute("""
        SELECT id, user_id, status, results, created_at, completed_at, time_range
        FROM analyses
        WHERE id = ?
    """, (analysis_id,))
    
    row = cursor.fetchone()
    if not row:
        print(f"❌ Analysis {analysis_id} not found")
        return
    
    print(f"✅ Found Analysis {analysis_id}")
    print(f"   Status: {row[2]}")
    print(f"   Created: {row[4]}")
    print(f"   Completed: {row[5]}")
    
    # Parse the results
    if row[3]:
        try:
            results = json.loads(row[3])
            
            # Check for AI insights
            print("\n📊 Checking AI Insights:")
            
            # Check if AI enhanced
            ai_enhanced = results.get('ai_enhanced', False)
            print(f"   ai_enhanced: {ai_enhanced}")
            
            # Check for ai_team_insights
            if 'ai_team_insights' in results:
                ai_insights = results['ai_team_insights']
                print(f"   ai_team_insights exists: ✅")
                print(f"   ai_team_insights.available: {ai_insights.get('available', False)}")
                
                if 'insights' in ai_insights:
                    insights = ai_insights['insights']
                    print(f"   Has insights object: ✅")
                    print(f"   Team size: {insights.get('team_size', 0)}")
                    print(f"   Data sources: {insights.get('data_sources', [])}")
                    
                    # Check for key components
                    if 'risk_distribution' in insights:
                        print(f"   Has risk_distribution: ✅")
                    if 'common_patterns' in insights:
                        print(f"   Has common_patterns: ✅ ({len(insights['common_patterns'])} patterns)")
                    if 'team_recommendations' in insights:
                        print(f"   Has team_recommendations: ✅ ({len(insights['team_recommendations'])} recommendations)")
                else:
                    print(f"   Has insights object: ❌")
            else:
                print(f"   ai_team_insights exists: ❌")
            
            # Check team_analysis
            print("\n📊 Checking Team Analysis:")
            if 'team_analysis' in results:
                team = results['team_analysis']
                print(f"   team_analysis exists: ✅")
                print(f"   Members count: {len(team.get('members', []))}")
            else:
                print(f"   team_analysis exists: ❌")
            
            # Check metadata
            print("\n📊 Checking Metadata:")
            if 'metadata' in results:
                meta = results['metadata']
                print(f"   Total incidents: {meta.get('total_incidents', 0)}")
                print(f"   Include GitHub: {meta.get('include_github', False)}")
                print(f"   Include Slack: {meta.get('include_slack', False)}")
            
            # Check analysis_data structure
            if 'analysis_data' in results:
                print("\n⚠️  Found nested analysis_data - possible double nesting issue")
                
            # Save full structure for inspection
            with open('analysis_115_structure.json', 'w') as f:
                json.dump(results, f, indent=2)
            print("\n💾 Full analysis structure saved to analysis_115_structure.json")
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse results JSON: {e}")
    else:
        print("❌ No results data found")
    
    conn.close()

if __name__ == "__main__":
    import sys
    analysis_id = int(sys.argv[1]) if len(sys.argv) > 1 else 115
    check_analysis(analysis_id)