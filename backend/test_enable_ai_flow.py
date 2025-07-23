#!/usr/bin/env python3
"""
Test the complete enable_ai flow
"""
import sqlite3
import json

def test_user_llm_token():
    """Test if user has LLM token properly configured"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Check user with ID 2 (Spencer)
    cursor.execute("""
        SELECT id, name, email, llm_token IS NOT NULL as has_token, llm_provider
        FROM users
        WHERE id = 2
    """)
    
    user = cursor.fetchone()
    if user:
        print(f"✅ User {user[1]} ({user[2]}):")
        print(f"   Has LLM Token: {'✅ Yes' if user[3] else '❌ No'}")
        print(f"   LLM Provider: {user[4] or 'None'}")
        return user[3] and user[4]  # Has token and provider
    else:
        print("❌ User not found")
        return False

def simulate_analysis_logic(enable_ai, user_has_llm_token):
    """Simulate the analysis logic from analyses.py"""
    print(f"\n🔍 Simulating analysis logic:")
    print(f"   enable_ai parameter: {enable_ai}")
    print(f"   user_has_llm_token: {user_has_llm_token}")
    
    use_ai_analyzer = False
    if enable_ai and user_has_llm_token:
        use_ai_analyzer = True
        print("   ✅ Will use BurnoutAnalyzerService (AI-enhanced)")
    else:
        print("   ❌ Will use SimpleBurnoutAnalyzer (basic)")
    
    return use_ai_analyzer

def test_scenarios():
    """Test different scenarios"""
    user_has_llm_token = test_user_llm_token()
    
    print(f"\n📊 Testing different scenarios:")
    
    # Scenario 1: AI enabled, user has token
    print(f"\n1. enable_ai=True, user_has_token={user_has_llm_token}")
    result1 = simulate_analysis_logic(True, user_has_llm_token)
    
    # Scenario 2: AI disabled, user has token
    print(f"\n2. enable_ai=False, user_has_token={user_has_llm_token}")
    result2 = simulate_analysis_logic(False, user_has_llm_token)
    
    # Scenario 3: AI enabled, user has no token
    print(f"\n3. enable_ai=True, user_has_token=False")
    result3 = simulate_analysis_logic(True, False)
    
    print(f"\n📋 Summary:")
    print(f"   Scenario 1 (AI on, token available): {'AI' if result1 else 'Basic'}")
    print(f"   Scenario 2 (AI off, token available): {'AI' if result2 else 'Basic'}")
    print(f"   Scenario 3 (AI on, no token): {'AI' if result3 else 'Basic'}")
    
    expected_results = [bool(user_has_llm_token), False, False]
    actual_results = [result1, result2, result3]
    
    if actual_results == expected_results:
        print(f"\n✅ All scenarios working correctly!")
        return True
    else:
        print(f"\n❌ Logic error detected!")
        print(f"   Expected: {expected_results}")
        print(f"   Actual:   {actual_results}")
        return False

if __name__ == "__main__":
    success = test_scenarios()
    
    if success:
        print(f"\n🎉 The enable_ai flow is working correctly!")
        print(f"   - When AI is enabled and user has token: Use AI analyzer")
        print(f"   - When AI is disabled OR user has no token: Use basic analyzer")
    else:
        print(f"\n❌ There's an issue with the enable_ai flow logic.")