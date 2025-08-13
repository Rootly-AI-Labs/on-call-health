#!/usr/bin/env python3
"""
Get the REAL organization names from Railway API tokens.
"""

import os
import sys
import asyncio

async def get_real_organization_names():
    """Get actual organization names from Railway environment tokens."""
    
    beta_rootly_token = os.getenv('ROOTLY_API_TOKEN')
    beta_pagerduty_token = os.getenv('PAGERDUTY_API_TOKEN')
    
    real_names = {}
    
    if beta_rootly_token:
        try:
            # Import inside function to avoid import issues
            sys.path.append('.')
            from app.core.rootly_client import RootlyAPIClient
            
            print(f"🔍 Testing Rootly API with Railway token...")
            rootly_client = RootlyAPIClient(beta_rootly_token)
            test_result = await rootly_client.test_connection()
            
            if test_result.get("status") == "success":
                account_info = test_result.get("account_info", {})
                org_name = account_info.get("organization_name")
                print(f"✅ Rootly organization: '{org_name}'")
                real_names['rootly'] = org_name
            else:
                print(f"❌ Rootly API failed: {test_result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"❌ Rootly API error: {str(e)}")
    
    if beta_pagerduty_token:
        try:
            from app.core.pagerduty_client import PagerDutyAPIClient
            
            print(f"🔍 Testing PagerDuty API with Railway token...")
            pagerduty_client = PagerDutyAPIClient(beta_pagerduty_token)
            test_result = await pagerduty_client.test_connection()
            
            if test_result.get("valid"):
                account_info = test_result.get("account_info", {})
                org_name = account_info.get("organization_name")
                print(f"✅ PagerDuty organization: '{org_name}'")
                real_names['pagerduty'] = org_name
            else:
                print(f"❌ PagerDuty API failed: {test_result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"❌ PagerDuty API error: {str(e)}")
    
    return real_names

if __name__ == "__main__":
    asyncio.run(get_real_organization_names())