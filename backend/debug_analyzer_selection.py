#!/usr/bin/env python3
"""
Debug the analyzer selection logic to understand why AI isn't being used
"""
import sqlite3

def debug_analyzer_logic():
    """Debug the analyzer selection logic for Analysis 117"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get analysis 117 details
    cursor.execute('SELECT id, user_id, status FROM analyses WHERE id = 117')
    analysis = cursor.fetchone()
    
    if not analysis:
        print("❌ Analysis 117 not found")
        return
    
    user_id = analysis[1]
    print(f"✅ Analysis 117 found, User ID: {user_id}")
    
    # Check user LLM configuration
    cursor.execute('SELECT id, name, llm_token IS NOT NULL as has_token, llm_provider FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    
    if user:
        print(f"✅ User {user[1]}:")
        print(f"   Has LLM Token: {user[2]}")
        print(f"   LLM Provider: {user[3]}")
        
        # Simulate the analyzer selection logic
        enable_ai = True  # Assuming this was set to True in the request
        use_ai_analyzer = False
        
        if enable_ai and user_id:
            if user[2] and user[3]:  # has_token and provider
                use_ai_analyzer = True
                print(f"✅ Should use AI analyzer: enable_ai={enable_ai}, has_token={user[2]}, provider={user[3]}")
            else:
                print(f"❌ Won't use AI analyzer: has_token={user[2]}, provider={user[3]}")
        else:
            print(f"❌ Won't use AI analyzer: enable_ai={enable_ai}, user_id={user_id}")
        
        analyzer_type = "BurnoutAnalyzerService (AI)" if use_ai_analyzer else "SimpleBurnoutAnalyzer (Basic)"
        print(f"📊 Should use: {analyzer_type}")
        
        # Check actual results to see what was used
        cursor.execute('SELECT results FROM analyses WHERE id = 117')
        results = cursor.fetchone()
        
        if results and results[0]:
            import json
            try:
                data = json.loads(results[0])
                ai_enhanced = data.get('ai_enhanced', False)
                has_ai_insights = 'ai_team_insights' in data
                
                print(f"\n📋 Actual results analysis:")
                print(f"   ai_enhanced flag: {ai_enhanced}")
                print(f"   Has ai_team_insights: {has_ai_insights}")
                
                if use_ai_analyzer and not ai_enhanced:
                    print("❌ MISMATCH: Should have used AI analyzer but ai_enhanced=False")
                elif not use_ai_analyzer and ai_enhanced:
                    print("❌ MISMATCH: Should have used basic analyzer but ai_enhanced=True")
                else:
                    print("✅ MATCH: Analyzer selection matches results")
                    
            except json.JSONDecodeError:
                print("❌ Could not parse results JSON")
    else:
        print("❌ User not found")
    
    conn.close()

if __name__ == "__main__":
    debug_analyzer_logic()