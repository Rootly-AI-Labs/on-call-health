#!/usr/bin/env python3
"""
Test script for the permissions checking endpoint.
"""

import requests
import json
import os

# Configuration
API_BASE = "http://localhost:8000"
AUTH_TOKEN = os.getenv('AUTH_TOKEN', 'your_auth_token_here')

def list_integrations():
    """List all integrations to find IDs to test with."""
    url = f"{API_BASE}/rootly/integrations"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.ok:
            result = response.json()
            integrations = result.get("integrations", [])
            
            print(f"Found {len(integrations)} integrations:")
            for integration in integrations:
                print(f"  ID: {integration['id']}, Name: {integration['name']}")
                if 'permissions' in integration:
                    perms = integration['permissions']
                    print(f"    Users: {'✅' if perms.get('users', {}).get('access') else '❌'}")
                    print(f"    Incidents: {'✅' if perms.get('incidents', {}).get('access') else '❌'}")
            
            return [i['id'] for i in integrations]
        else:
            print(f"Failed to list integrations: {response.text}")
            return []
            
    except Exception as e:
        print(f"Exception listing integrations: {str(e)}")
        return []

def test_permissions(integration_id: int):
    """Test the permissions endpoint for a specific integration."""
    url = f"{API_BASE}/rootly/integrations/{integration_id}/permissions"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting permissions for integration {integration_id}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("✅ Success!")
            print(f"Integration: {result['integration_name']}")
            print(f"Status: {result['status']}")
            
            print("\nPermissions:")
            for perm_type, perm_data in result['permissions'].items():
                access = "✅" if perm_data.get('access') else "❌"
                error_msg = f" ({perm_data.get('error')})" if perm_data.get('error') else ""
                print(f"  {perm_type}: {access}{error_msg}")
            
            print("\nRecommendations:")
            for rec in result['recommendations']:
                icon = "✅" if rec['type'] == 'success' else "❌"
                print(f"  {icon} {rec['title']}: {rec['message']}")
                if rec.get('action'):
                    print(f"     Action: {rec['action']}")
        else:
            print("❌ Failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def main():
    """Main test function."""
    print("=== Testing Permissions Checking Endpoint ===\n")
    
    if AUTH_TOKEN == 'your_auth_token_here':
        print("⚠️  Please set AUTH_TOKEN environment variable with a valid token")
        print("   Example: export AUTH_TOKEN='your_actual_token'")
        return
    
    # List existing integrations
    print("1. Listing existing integrations...\n")
    integration_ids = list_integrations()
    
    if not integration_ids:
        print("No integrations found to test with")
        return
    
    # Test with the first integration
    test_integration_id = integration_ids[0]
    print(f"\n2. Testing permissions check for integration ID {test_integration_id}...")
    
    test_permissions(test_integration_id)

if __name__ == "__main__":
    main()