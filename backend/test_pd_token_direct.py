#!/usr/bin/env python3
"""
Direct test of PagerDuty token from database
"""
import asyncio
import aiohttp
import sqlite3
import sys

async def test_pagerduty_token_direct():
    """Test PagerDuty token directly"""
    # Get the token from database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, name, api_token, organization_name, platform
        FROM rootly_integrations 
        WHERE platform = 'pagerduty' AND user_id = 2
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("❌ No PagerDuty integration found for user 2")
        return
    
    integration_id, name, token, org_name, platform = result
    print(f"📊 PagerDuty Integration Details:")
    print(f"   ID: {integration_id}")
    print(f"   Name: {name}")
    print(f"   Organization: {org_name}")
    print(f"   Platform: {platform}")
    print(f"   Token exists: {'Yes' if token else 'No'}")
    print(f"   Token length: {len(token) if token else 0}")
    
    if not token:
        print("❌ No token found!")
        return
    
    print(f"\n🔍 Testing PagerDuty API with token...")
    
    # Test the token with PagerDuty API
    headers = {
        "Authorization": f"Token token={token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Get current user
        print("\n1️⃣ Testing /users/me endpoint...")
        try:
            async with session.get(
                "https://api.pagerduty.com/users/me",
                headers=headers
            ) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    user = data.get('user', {})
                    print(f"   ✅ SUCCESS - Token is valid!")
                    print(f"   User: {user.get('name', 'Unknown')}")
                    print(f"   Email: {user.get('email', 'Unknown')}")
                elif response.status == 401:
                    print(f"   ❌ UNAUTHORIZED - Token is invalid!")
                    error_text = await response.text()
                    print(f"   Error: {error_text[:200]}")
                else:
                    print(f"   ⚠️ Unexpected status: {response.status}")
                    error_text = await response.text()
                    print(f"   Response: {error_text[:200]}")
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")
        
        # Test 2: Get incidents
        print("\n2️⃣ Testing /incidents endpoint...")
        try:
            async with session.get(
                "https://api.pagerduty.com/incidents?limit=1",
                headers=headers
            ) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Can access incidents")
                    print(f"   Total incidents: {data.get('total', 'Unknown')}")
                else:
                    print(f"   ❌ Cannot access incidents")
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")
        
        # Test 3: Get users
        print("\n3️⃣ Testing /users endpoint...")
        try:
            async with session.get(
                "https://api.pagerduty.com/users?limit=1",
                headers=headers
            ) as response:
                print(f"   Status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   ✅ Can access users")
                    print(f"   Total users: {data.get('total', 'Unknown')}")
                else:
                    print(f"   ❌ Cannot access users")
        except Exception as e:
            print(f"   ❌ Request failed: {str(e)}")

if __name__ == "__main__":
    print("🔧 Direct PagerDuty Token Test")
    print("=" * 50)
    asyncio.run(test_pagerduty_token_direct())