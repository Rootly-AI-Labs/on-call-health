#!/usr/bin/env python3
"""
Test API endpoints to see what they return
"""

import requests
import json

API_BASE = "http://localhost:8000"

def test_endpoint(endpoint, description, headers=None):
    print(f"\n🔍 Testing {description}")
    print(f"📍 URL: {API_BASE}{endpoint}")
    
    try:
        response = requests.get(f"{API_BASE}{endpoint}", headers=headers)
        print(f"📊 Status: {response.status_code}")
        print(f"📄 Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"✅ Response: {json.dumps(data, indent=2)}")
            except:
                print(f"✅ Response (text): {response.text}")
        else:
            print(f"❌ Error response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_endpoints():
    print("🚀 Testing API endpoints...")
    
    # Test health endpoint
    test_endpoint("/health", "Health check")
    
    # Test root endpoint  
    test_endpoint("/", "Root endpoint")
    
    # Test protected endpoints without auth
    test_endpoint("/rootly/integrations", "Rootly integrations (no auth)")
    test_endpoint("/pagerduty/integrations", "PagerDuty integrations (no auth)")
    test_endpoint("/integrations/github/status", "GitHub status (no auth)")
    test_endpoint("/integrations/slack/status", "Slack status (no auth)")
    test_endpoint("/analyses", "Analyses (no auth)")
    
    # Test with dummy auth header
    headers = {"Authorization": "Bearer dummy-token"}
    test_endpoint("/rootly/integrations", "Rootly integrations (with dummy auth)", headers)
    
    print("\n🔍 Summary: The frontend likely needs to send proper authentication headers!")

if __name__ == "__main__":
    test_endpoints()