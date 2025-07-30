#!/usr/bin/env python3
"""
Test script for the data consistency checking endpoint.
"""

import requests
import json
import os

# Configuration
API_BASE = "http://localhost:8000"
AUTH_TOKEN = os.getenv('AUTH_TOKEN', 'your_auth_token_here')

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

def test_consistency_check(analysis_id: int):
    """Test the consistency check endpoint for a specific analysis."""
    url = f"{API_BASE}/analyses/{analysis_id}/verify-consistency"
    headers = {
        "Authorization": f"Bearer {AUTH_TOKEN}",
        "Content-Type": "application/json"
    }
    
    print(f"\nTesting consistency check for analysis {analysis_id}")
    print(f"URL: {url}")
    
    try:
        response = requests.get(url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.ok:
            result = response.json()
            print("✅ Success!")
            
            # Display summary
            summary = result.get('summary', {})
            print(f"\n=== CONSISTENCY SUMMARY ===")
            print(f"Overall Consistency: {'✅ PASS' if result.get('overall_consistency') else '❌ FAIL'}")
            print(f"Consistency Score: {summary.get('consistency_percentage', 0)}%")
            print(f"Checks Passed: {summary.get('checks_passed', 0)}/{summary.get('total_checks', 0)}")
            print(f"Critical Issues: {summary.get('critical_issues_count', 0)}")
            print(f"Warnings: {summary.get('warnings_count', 0)}")
            
            # Display detailed checks
            print(f"\n=== DETAILED CHECKS ===")
            for check_name, check_data in result.get('consistency_checks', {}).items():
                status = "✅ PASS" if check_data.get('match') else "❌ FAIL"
                print(f"{check_name}: {status}")
                
                # Show key metrics for this check
                for key, value in check_data.items():
                    if key not in ['match', 'discrepancies'] and not key.endswith('_calculation'):
                        print(f"  {key}: {value}")
                
                # Show discrepancies if any
                if check_data.get('discrepancies'):
                    for discrepancy in check_data['discrepancies']:
                        print(f"  ⚠️  {discrepancy}")
            
            # Show critical issues
            if result.get('critical_issues'):
                print(f"\n=== CRITICAL ISSUES ===")
                for issue in result['critical_issues']:
                    print(f"❌ {issue}")
                    
            # Show warnings
            if result.get('warnings'):
                print(f"\n=== WARNINGS ===")
                for warning in result['warnings']:
                    print(f"⚠️  {warning}")
                    
            if result.get('overall_consistency'):
                print(f"\n🎉 Analysis {analysis_id} has consistent data across all components!")
            else:
                print(f"\n⚠️  Analysis {analysis_id} has data consistency issues that need attention.")
                
        else:
            print("❌ Failed!")
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

def main():
    """Main test function."""
    print("=== Testing Data Consistency Checking Endpoint ===\n")
    
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
    
    # Test with the first few completed analyses
    test_count = min(3, len(analysis_ids))
    
    for i in range(test_count):
        test_analysis_id = analysis_ids[i]
        print(f"\n{'='*50}")
        print(f"Testing analysis {i+1}/{test_count}: ID {test_analysis_id}")
        print(f"{'='*50}")
        
        test_consistency_check(test_analysis_id)
        
        if i < test_count - 1:
            print(f"\n{'-'*30}")

if __name__ == "__main__":
    main()