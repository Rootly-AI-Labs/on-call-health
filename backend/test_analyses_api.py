#!/usr/bin/env python3
"""
Test the analyses API endpoint directly
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_analyses_api():
    print("🔍 Testing /analyses API endpoint...")
    
    try:
        # Test without auth first
        print("\n📍 Testing without authentication...")
        response = requests.get(f"{API_BASE}/analyses")
        print(f"Status: {response.status_code}")
        if response.status_code == 401:
            print("✅ Correctly requires authentication")
        else:
            print(f"Response: {response.text[:200]}...")
        
        # Test with dummy auth
        print("\n📍 Testing with dummy auth token...")
        headers = {"Authorization": "Bearer dummy-token"}
        response = requests.get(f"{API_BASE}/analyses", headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
        
        # Check what the actual user would see
        print("\n📍 Checking auth requirements...")
        response = requests.get(f"{API_BASE}/auth/me")
        print(f"Auth me status: {response.status_code}")
        if response.status_code != 200:
            print("❌ Auth endpoint not working - user needs to login")
        
    except Exception as e:
        print(f"❌ Error testing API: {e}")

if __name__ == "__main__":
    test_analyses_api()