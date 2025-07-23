#!/usr/bin/env python3
import sqlite3
import requests

# Get PagerDuty integration
conn = sqlite3.connect('test.db')
cursor = conn.cursor()
cursor.execute("SELECT id, name, api_token FROM rootly_integrations WHERE platform = 'pagerduty' LIMIT 1")
result = cursor.fetchone()
conn.close()

if result:
    integration_id, name, token = result
    print(f"PagerDuty Integration: {name}")
    print(f"Token exists: {bool(token)}")
    print(f"Token length: {len(token) if token else 0}")
    
    if token:
        # Test the token
        headers = {
            "Authorization": f"Token token={token}",
            "Accept": "application/vnd.pagerduty+json;version=2"
        }
        
        print("\nTesting token...")
        response = requests.get("https://api.pagerduty.com/users/me", headers=headers)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Token is valid!")
            print(f"User: {user_data.get('user', {}).get('name', 'Unknown')}")
        else:
            print(f"❌ Token is invalid or has insufficient permissions")
            print(f"Response: {response.text[:200]}...")
else:
    print("No PagerDuty integration found")