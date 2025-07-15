#!/usr/bin/env python3
"""
Debug AI insights in analysis results
"""
import sqlite3
import json
import sys
import os

def debug_latest_analysis():
    """Check the latest analysis for AI insights data."""
    db_path = os.path.join(os.path.dirname(__file__), 'test.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the latest analysis
        cursor.execute("""
            SELECT id, status, results, created_at 
            FROM analyses 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if not result:
            print("❌ No analyses found")
            return
        
        analysis_id, status, results_json, created_at = result
        
        print(f"🔍 Latest Analysis Debug")
        print(f"   ID: {analysis_id}")
        print(f"   Status: {status}")
        print(f"   Created: {created_at}")
        
        if not results_json:
            print("❌ No results found")
            return
        
        try:
            analysis_data = json.loads(results_json)
            
            # Check for AI team insights
            ai_insights = analysis_data.get('ai_team_insights')
            print(f"\n🤖 AI Team Insights:")
            
            if ai_insights:
                print(f"   ✅ ai_team_insights exists")
                print(f"   Available: {ai_insights.get('available', False)}")
                
                if ai_insights.get('insights'):
                    insights = ai_insights['insights']
                    print(f"   Team size: {insights.get('team_size', 'unknown')}")
                    print(f"   Data sources: {insights.get('data_sources', [])}")
                    print(f"   Risk distribution: {bool(insights.get('risk_distribution'))}")
                    print(f"   Common patterns: {len(insights.get('common_patterns', []))}")
                    print(f"   Team recommendations: {len(insights.get('team_recommendations', []))}")
                else:
                    print("   ❌ No insights data found")
            else:
                print("   ❌ ai_team_insights not found")
            
            # Check individual member AI insights
            team_analysis = analysis_data.get('team_analysis', {})
            members = team_analysis.get('members', [])
            
            ai_enhanced_members = 0
            for member in members:
                if 'ai_insights' in member or 'ai_risk_assessment' in member:
                    ai_enhanced_members += 1
            
            print(f"\n👥 Individual Members:")
            print(f"   Total members: {len(members)}")
            print(f"   AI-enhanced members: {ai_enhanced_members}")
            
            # Check if user has LLM token
            cursor.execute("SELECT llm_token, llm_provider FROM users WHERE id = (SELECT user_id FROM analyses WHERE id = ? LIMIT 1)", (analysis_id,))
            user_result = cursor.fetchone()
            
            if user_result:
                llm_token, llm_provider = user_result
                print(f"\n🔑 User LLM Config:")
                print(f"   Has token: {bool(llm_token)}")
                print(f"   Provider: {llm_provider or 'None'}")
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse results JSON: {e}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    debug_latest_analysis()