#!/usr/bin/env python3
"""
Test script for the trends regeneration endpoint.
"""

import requests
import json
import os

# Configuration
API_BASE = "http://localhost:8000"
AUTH_TOKEN = os.getenv('AUTH_TOKEN', 'your_auth_token_here')

def test_regenerate_trends(analysis_id: int):
    """Test the regenerate trends endpoint for a specific analysis."""
    url = f"{API_BASE}/analyses/{analysis_id}/regenerate-trends"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"Testing trends regeneration for analysis {analysis_id}")
    print(f"URL: {url}")
    
    try:
        response = requests.post(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.ok:
            result = response.json()
            print("✅ Success!")
            print(json.dumps(result, indent=2))
        else:
            print("❌ Failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def list_analyses():
    """List all analyses to find IDs to test with."""
    url = f"{API_BASE}/analyses"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}"
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.ok:
            result = response.json()
            analyses = result.get("analyses", [])
            
            print(f"Found {len(analyses)} analyses:")
            for analysis in analyses[:10]:  # Show first 10
                print(f"  ID: {analysis['id']}, Status: {analysis['status']}, Created: {analysis['created_at']}")
            
            return [a['id'] for a in analyses if a['status'] == 'completed']
        else:
            print(f"Failed to list analyses: {response.text}")
            return []
            
    except Exception as e:
        print(f"Exception listing analyses: {str(e)}")
        return []

def main():
    """Main test function."""
    print("=== Testing Trends Regeneration Endpoint ===\n")
    
    if AUTH_TOKEN == 'your_auth_token_here':
        print("⚠️  Please set AUTH_TOKEN environment variable with a valid token")
        print("   Example: export AUTH_TOKEN='your_actual_token'")
        return
    
    # List existing analyses
    print("1. Listing existing analyses...\n")
    analysis_ids = list_analyses()
    
    if not analysis_ids:
        print("No completed analyses found to test with")
        return
    
    # Test with the first completed analysis
    test_analysis_id = analysis_ids[0]
    print(f"\n2. Testing regeneration with analysis ID {test_analysis_id}...\n")
    
    test_regenerate_trends(test_analysis_id)
    
    print(f"\n3. Testing again (should show 'already exists')...\n")
    test_regenerate_trends(test_analysis_id)

if __name__ == "__main__":
    main()