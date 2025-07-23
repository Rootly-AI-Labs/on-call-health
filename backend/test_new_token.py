#!/usr/bin/env python3
"""
Test the new PagerDuty token
"""
import asyncio
from app.core.pagerduty_client import PagerDutyAPIClient

async def test_new_token():
    """Test the new token directly"""
    token = "u+yHcJXSxpjyRijaQR9g"
    
    print(f"🔍 Testing new PagerDuty token: {token[:10]}...")
    
    client = PagerDutyAPIClient(token)
    
    try:
        # Test connection exactly like the endpoint does
        result = await client.test_connection()
        
        print(f"\n📊 Test Connection Result:")
        print(f"   Valid: {result.get('valid', False)}")
        
        if result.get('valid'):
            account_info = result.get('account_info', {})
            print(f"   ✅ SUCCESS!")
            print(f"   Organization: {account_info.get('organization_name', 'Unknown')}")
            print(f"   Current User: {account_info.get('current_user', 'Unknown')}")
            print(f"   Total Users: {account_info.get('total_users', 0)}")
            print(f"   Total Services: {account_info.get('total_services', 0)}")
        else:
            print(f"   ❌ FAILED!")
            print(f"   Error: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"\n❌ Exception occurred: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_new_token())