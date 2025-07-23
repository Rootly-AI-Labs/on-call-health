#!/usr/bin/env python3
"""
Test PagerDuty API token validity
"""
import asyncio
import sqlite3
from app.core.pagerduty_client import PagerDutyAPIClient

async def test_pagerduty_token():
    """Test if the PagerDuty token is valid"""
    # Get the token from the database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get the most recent PagerDuty integration
    cursor.execute("""
        SELECT id, name, api_token, organization_name 
        FROM rootly_integrations 
        WHERE platform = 'pagerduty' 
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    integration = cursor.fetchone()
    conn.close()
    
    if not integration:
        print("❌ No PagerDuty integration found")
        return
    
    integration_id, name, api_token, org_name = integration
    print(f"✅ Found PagerDuty integration: {name} (ID: {integration_id})")
    print(f"   Organization: {org_name}")
    print(f"   Token length: {len(api_token) if api_token else 0}")
    print(f"   Token prefix: {api_token[:10]}..." if api_token else "No token")
    
    if not api_token:
        print("❌ No API token found")
        return
    
    # Test the token
    print("\n🔍 Testing PagerDuty API connection...")
    client = PagerDutyAPIClient(api_token)
    
    try:
        # Test connection
        result = await client.test_connection()
        print(f"\n📊 Connection test result:")
        print(f"   Valid: {result.get('valid', False)}")
        
        if result.get('valid'):
            account_info = result.get('account_info', {})
            print(f"   ✅ Connection successful!")
            print(f"   Organization: {account_info.get('organization_name', 'Unknown')}")
            print(f"   Current User: {account_info.get('current_user', 'Unknown')}")
            print(f"   Total Users: {account_info.get('total_users', 0)}")
            print(f"   Total Services: {account_info.get('total_services', 0)}")
        else:
            print(f"   ❌ Connection failed: {result.get('error', 'Unknown error')}")
            
        # Try to fetch some data
        print("\n🔍 Testing data collection...")
        data = await client.collect_analysis_data(days_back=30)
        
        users = data.get('users', [])
        incidents = data.get('incidents', [])
        metadata = data.get('collection_metadata', {})
        
        print(f"\n📊 Data collection results:")
        print(f"   Users collected: {len(users)}")
        print(f"   Incidents collected: {len(incidents)}")
        print(f"   Days analyzed: {metadata.get('days_analyzed', 0)}")
        
        if metadata.get('error'):
            print(f"   ❌ Error during collection: {metadata['error']}")
        else:
            print(f"   ✅ Data collection successful!")
            
    except Exception as e:
        print(f"\n❌ Error testing PagerDuty API: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pagerduty_token())