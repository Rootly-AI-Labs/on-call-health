#!/usr/bin/env python3
"""
List PagerDuty services to find service IDs
"""

import requests
import json

def list_services(api_token):
    headers = {
        "Authorization": f"Token token={api_token}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json"
    }
    
    response = requests.get(
        "https://api.pagerduty.com/services",
        headers=headers
    )
    
    if response.status_code == 200:
        services = response.json()["services"]
        print("\nYour PagerDuty Services:")
        print("=" * 60)
        for service in services:
            print(f"\nService Name: {service['name']}")
            print(f"Service ID: {service['id']}")
            print(f"Status: {service['status']}")
            print(f"Description: {service.get('description', 'No description')}")
            print("-" * 60)
        return services
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    api_token = "u+yU3VeLnT_d1HuYzDrg"
    services = list_services(api_token)
    
    if services:
        print(f"\nTotal services found: {len(services)}")
        if len(services) > 0:
            print(f"\nTo create incidents, use one of the Service IDs above")
            print(f"Example: python create_pagerduty_incidents.py --token {api_token} --service-id {services[0]['id']} --count 10")