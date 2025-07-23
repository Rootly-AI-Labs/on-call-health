#!/usr/bin/env python3
"""
Check if user has LLM tokens configured
"""
import sqlite3
import json

def check_user_llm(analysis_id):
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get the user_id from the analysis
    cursor.execute("SELECT user_id FROM analyses WHERE id = ?", (analysis_id,))
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ Analysis {analysis_id} not found")
        return
    
    user_id = row[0]
    print(f"✅ Found analysis {analysis_id} for user_id: {user_id}")
    
    # Check user's LLM configuration
    cursor.execute("""
        SELECT id, name, email, llm_token IS NOT NULL as has_token, llm_provider
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    if user:
        print(f"\n👤 User Info:")
        print(f"   Name: {user[1]}")
        print(f"   Email: {user[2]}")
        print(f"   Has LLM Token: {'✅ Yes' if user[3] else '❌ No'}")
        print(f"   LLM Provider: {user[4] or 'None'}")
    
    conn.close()

if __name__ == "__main__":
    check_user_llm(115)