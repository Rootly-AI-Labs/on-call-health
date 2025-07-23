#!/usr/bin/env python3
"""
Test script to check the /analyses/trends/historical endpoint directly
"""
import requests
import json
import sqlite3
from datetime import datetime, timedelta

# Check database first to see what data exists
print("=== CHECKING DATABASE ===")
conn = sqlite3.connect('test.db')
cursor = conn.cursor()

# Get recent completed analyses
cursor.execute('''
    SELECT id, user_id, rootly_integration_id, status, created_at, completed_at
    FROM analyses 
    WHERE status = 'completed' 
    AND created_at >= date('now', '-30 days')
    ORDER BY created_at DESC
    LIMIT 10
''')

analyses = cursor.fetchall()
print(f"Found {len(analyses)} completed analyses in last 30 days:")
for analysis in analyses:
    print(f"  Analysis {analysis[0]}: user_id={analysis[1]}, integration_id={analysis[2]}, created={analysis[4]}")

# Get users
cursor.execute('SELECT id, email FROM users LIMIT 5')
users = cursor.fetchall()
print(f"\nFound {len(users)} users:")
for user in users:
    print(f"  User {user[0]}: {user[1]}")

# Get integrations
cursor.execute('SELECT id, user_id, platform FROM rootly_integrations WHERE is_active = 1 LIMIT 5')
integrations = cursor.fetchall()
print(f"\nFound {len(integrations)} active integrations:")
for integration in integrations:
    print(f"  Integration {integration[0]}: user_id={integration[1]}, platform={integration[2]}")

conn.close()

# Test the API endpoint
print("\n=== TESTING API ENDPOINT ===")

# First, let's check what auth token we might need
# We need to create a test JWT token or use existing one
base_url = "http://localhost:8000"

# Test without auth first to see the error
try:
    print("\n1. Testing without authentication:")
    response = requests.get(f"{base_url}/analyses/trends/historical")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")

# Now let's try to get a proper auth token if we have user data
if users:
    user_id = users[0][0]  # Use first user
    print(f"\n2. Testing with user_id {user_id}:")
    
    # Try to get/create a JWT token (you might need to adjust this)
    try:
        # First check if there's an existing token we can use
        import os
        import sys
        sys.path.append('/Users/spencercheng/Workspace/Rootly/rootly-burnout-detector-web/backend')
        
        from app.auth.jwt import create_access_token
        
        # Create a token for the test user
        access_token = create_access_token(data={"sub": str(user_id)})
        print(f"Created token: {access_token[:20]}...")
        
        # Test the endpoint with authentication
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Test with different parameters
        test_params = [
            {"days_back": "14"},
            {"days_back": "30"},
            {"days_back": "7"},
        ]
        
        if integrations:
            integration_id = integrations[0][0]
            test_params.append({"days_back": "14", "integration_id": str(integration_id)})
        
        for params in test_params:
            print(f"\n   Testing with params: {params}")
            response = requests.get(f"{base_url}/analyses/trends/historical", 
                                  headers=headers, params=params)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Daily trends count: {len(data.get('daily_trends', []))}")
                print(f"   Timeline events count: {len(data.get('timeline_events', []))}")
                print(f"   Date range: {data.get('date_range', {})}")
                
                if data.get('daily_trends'):
                    print("   Sample daily trends:")
                    for trend in data['daily_trends'][:3]:
                        print(f"     {trend.get('date')}: score={trend.get('overall_score')}, at_risk={trend.get('members_at_risk')}")
                else:
                    print("   NO DAILY TRENDS DATA!")
                    
                # Print the full response for debugging
                print(f"   Full response: {json.dumps(data, indent=2)}")
            else:
                print(f"   Error response: {response.text}")
                
    except Exception as e:
        print(f"Error creating/testing with token: {e}")
        import traceback
        traceback.print_exc()

print("\n=== SUMMARY ===")
print("If daily_trends is empty, the issue could be:")
print("1. No completed analyses with valid results data")
print("2. Analyses don't have the expected team_health structure") 
print("3. Date filtering is too restrictive")
print("4. Database schema issues")