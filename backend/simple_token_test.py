#!/usr/bin/env python3
import requests

token = "u+yU3VeLnT_d1HuYzDrg"

headers = {
    "Authorization": f"Token token={token}",
    "Accept": "application/vnd.pagerduty+json;version=2"
}

print(f"Testing PagerDuty token: {token[:10]}...")

try:
    response = requests.get("https://api.pagerduty.com/users/me", headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        user = data.get('user', {})
        print(f"✅ TOKEN IS VALID!")
        print(f"User: {user.get('name', 'Unknown')}")
        print(f"Email: {user.get('email', 'Unknown')}")
    else:
        print(f"❌ TOKEN IS INVALID!")
        print(f"Response: {response.text[:200]}")
        
except Exception as e:
    print(f"Error: {e}")