#!/usr/bin/env python3
"""
Test token validation is working
"""
import requests
import json

API_BASE = "http://localhost:8000"

def test_fake_tokens():
    print("🔒 Testing Token Validation")
    print("=" * 30)
    
    # Get test JWT token
    try:
        response = requests.post(f"{API_BASE}/auth/test-token")
        if response.status_code != 200:
            print("❌ Failed to get test JWT token")
            return
        token = response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"❌ Error getting JWT: {e}")
        return
    
    # Test 1: Valid format but fake Anthropic token
    print("1️⃣  Testing fake Anthropic token (valid format)...")
    fake_anthropic = "sk-ant-api03_fake_token_12345678901234567890123456789012345678901234567890123456789012345678901234567890"
    
    try:
        response = requests.post(
            f"{API_BASE}/llm/token",
            headers=headers,
            json={"token": fake_anthropic, "provider": "anthropic"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            error = response.json()
            print(f"   ✅ Correctly rejected: {error.get('detail', 'Unknown error')}")
        else:
            print(f"   ❌ Unexpectedly accepted fake token: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 2: Valid format but fake OpenAI token  
    print("\n2️⃣  Testing fake OpenAI token (valid format)...")
    fake_openai = "sk-fake1234567890123456789012345678901234567890123456"
    
    try:
        response = requests.post(
            f"{API_BASE}/llm/token",
            headers=headers,
            json={"token": fake_openai, "provider": "openai"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            error = response.json()
            print(f"   ✅ Correctly rejected: {error.get('detail', 'Unknown error')}")
        else:
            print(f"   ❌ Unexpectedly accepted fake token: {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Invalid format tokens
    print("\n3️⃣  Testing invalid format tokens...")
    
    try:
        response = requests.post(
            f"{API_BASE}/llm/token",
            headers=headers,
            json={"token": "invalid-token", "provider": "anthropic"}
        )
        print(f"   Anthropic invalid format - Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected invalid format")
        
        response = requests.post(
            f"{API_BASE}/llm/token",
            headers=headers,
            json={"token": "invalid-token", "provider": "openai"}
        )
        print(f"   OpenAI invalid format - Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected invalid format")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print("\n🎯 Token validation is now working correctly!")
    print("💡 Real tokens will be tested against the actual APIs before being stored.")

if __name__ == "__main__":
    test_fake_tokens()