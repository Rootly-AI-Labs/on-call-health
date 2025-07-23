#!/usr/bin/env python3
"""
Test the /analyses/trends/historical API endpoint directly
"""
import requests
import json
from datetime import datetime, timedelta
import jwt

def create_test_token():
    """Create a JWT token for testing"""
    payload = {
        "sub": "2",  # User ID from our database check
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    
    # Use the same secret that should be in the FastAPI app
    secret = "your-secret-key-change-in-production-use-openssl-rand-hex-32"  # From .env file
    
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token

def test_trends_endpoint():
    """Test the historical trends endpoint"""
    
    try:
        # Create auth token
        auth_token = create_test_token()
        print(f"Created auth token: {auth_token[:20]}...")
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        base_url = "http://localhost:8000"
        
        # Test different parameter combinations
        test_cases = [
            {"days_back": "14"},
            {"days_back": "7"}, 
            {"days_back": "30"},
            {"days_back": "14", "integration_id": "4"},  # PagerDuty integration from our DB check
            {"days_back": "14", "integration_id": "3"},  # Rootly integration from our DB check
        ]
        
        for i, params in enumerate(test_cases):
            print(f"\n=== TEST CASE {i+1}: {params} ===")
            
            try:
                response = requests.get(
                    f"{base_url}/analyses/trends/historical",
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                print(f"Status Code: {response.status_code}")
                print(f"Response Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    data = response.json()
                    
                    print(f"✅ Success! Response structure:")
                    print(f"   daily_trends: {len(data.get('daily_trends', []))} items")
                    print(f"   timeline_events: {len(data.get('timeline_events', []))} items") 
                    print(f"   summary: {data.get('summary', {})}")
                    print(f"   date_range: {data.get('date_range', {})}")
                    
                    # Show sample daily trends
                    daily_trends = data.get('daily_trends', [])
                    if daily_trends:
                        print(f"   Sample daily trends:")
                        for trend in daily_trends[:3]:
                            print(f"     {trend.get('date')}: score={trend.get('overall_score')}, at_risk={trend.get('members_at_risk')}")
                    else:
                        print("   ❌ NO DAILY TRENDS DATA - This is the issue!")
                        
                    # Print first few characters of full response for debugging
                    print(f"   Raw response (first 500 chars): {json.dumps(data)[:500]}...")
                    
                elif response.status_code == 403:
                    print("❌ Authentication failed - token might be invalid")
                    print(f"Response: {response.text}")
                elif response.status_code == 500:
                    print("❌ Server error")
                    print(f"Response: {response.text}")
                else:
                    print(f"❌ Unexpected status code")
                    print(f"Response: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ Request failed: {e}")
                
    except Exception as e:
        print(f"❌ Test setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("=== TESTING /analyses/trends/historical ENDPOINT ===")
    test_trends_endpoint()