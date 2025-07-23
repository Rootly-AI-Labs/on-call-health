#!/usr/bin/env python3
"""
Test specific PagerDuty token
"""
import asyncio
import aiohttp

async def test_token():
    """Test the specific PagerDuty token"""
    token = "u+yU3VeLnT_d1HuYzDrg"
    
    print(f"🔍 Testing PagerDuty token: {token[:10]}...")
    
    headers = {
        "Authorization": f"Token token={token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        # Test the token
        print("\n📡 Calling PagerDuty API /users/me...")
        try:
            async with session.get(
                "https://api.pagerduty.com/users/me",
                headers=headers
            ) as response:
                print(f"Status Code: {response.status}")
                print(f"Status Text: {response.reason}")
                
                response_text = await response.text()
                
                if response.status == 200:
                    import json
                    data = json.loads(response_text)
                    user = data.get('user', {})
                    print(f"\n✅ TOKEN IS VALID!")
                    print(f"User: {user.get('name', 'Unknown')}")
                    print(f"Email: {user.get('email', 'Unknown')}")
                    print(f"Role: {user.get('role', 'Unknown')}")
                else:
                    print(f"\n❌ TOKEN IS INVALID!")
                    print(f"Response: {response_text}")
                    
        except Exception as e:
            print(f"\n❌ Request failed: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_token())