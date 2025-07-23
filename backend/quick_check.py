#!/usr/bin/env python3
import sqlite3
import json

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# Get the most recent analysis
cursor.execute("SELECT id, user_id, status, results, created_at FROM analyses ORDER BY created_at DESC LIMIT 1")
row = cursor.fetchone()

if row:
    analysis_id, user_id, status, results, created_at = row
    print(f"Most recent analysis: {analysis_id}")
    print(f"Status: {status}")
    print(f"Created: {created_at}")
    print(f"User ID: {user_id}")
    
    # Check user LLM config
    cursor.execute("SELECT llm_token IS NOT NULL, llm_provider FROM users WHERE id = ?", (user_id,))
    user_row = cursor.fetchone()
    if user_row:
        print(f"User has LLM token: {user_row[0]}")
        print(f"LLM provider: {user_row[1]}")
    
    # Check analysis results
    if results:
        try:
            data = json.loads(results)
            print(f"ai_enhanced: {data.get('ai_enhanced', 'Not found')}")
            print(f"ai_team_insights exists: {'ai_team_insights' in data}")
            print(f"Main keys: {list(data.keys())}")
        except:
            print("Could not parse results")
else:
    print("No analyses found")

conn.close()