#!/usr/bin/env python3
"""
Test script to verify enable_ai flag is working
"""
import sqlite3
import json
from datetime import datetime

def test_recent_analysis():
    """Check the most recent analysis to see if enable_ai flag was used"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get the most recent analysis
    cursor.execute("""
        SELECT id, user_id, status, results, created_at, completed_at
        FROM analyses
        ORDER BY created_at DESC
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if not row:
        print("❌ No analyses found")
        return
    
    analysis_id = row[0]
    user_id = row[1]
    status = row[2]
    results = row[3]
    created_at = row[4]
    
    print(f"✅ Most recent analysis: {analysis_id}")
    print(f"   Status: {status}")
    print(f"   Created: {created_at}")
    print(f"   User ID: {user_id}")
    
    # Check user LLM config
    cursor.execute("""
        SELECT llm_token IS NOT NULL as has_token, llm_provider
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    user_row = cursor.fetchone()
    if user_row:
        print(f"   User has LLM token: {'✅' if user_row[0] else '❌'}")
        print(f"   LLM provider: {user_row[1] or 'None'}")
    
    # Check analysis results
    if results:
        try:
            data = json.loads(results)
            print(f"   ai_enhanced: {data.get('ai_enhanced', 'Not found')}")
            print(f"   ai_team_insights: {'✅' if 'ai_team_insights' in data else '❌'}")
        except json.JSONDecodeError:
            print("   ❌ Could not parse results JSON")
    
    conn.close()

if __name__ == "__main__":
    test_recent_analysis()