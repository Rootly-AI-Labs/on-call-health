#!/usr/bin/env python3
"""
Test script to verify the trends/historical endpoint is working
"""
import requests
import json

# Test the endpoint directly
API_BASE = "http://localhost:8000"
endpoint = f"{API_BASE}/analyses/trends/historical"

print(f"Testing endpoint: {endpoint}")

# Test without auth (should return 403)
try:
    response = requests.get(endpoint)
    print(f"No auth: Status {response.status_code}")
    if response.status_code != 403:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"No auth error: {e}")

# Test with invalid auth (should return 401 or 403)
try:
    headers = {"Authorization": "Bearer invalid_token"}
    response = requests.get(endpoint, headers=headers)
    print(f"Invalid auth: Status {response.status_code}")
    if response.status_code not in [401, 403]:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"Invalid auth error: {e}")

# Test the main analyses endpoint for comparison
try:
    main_endpoint = f"{API_BASE}/analyses"
    response = requests.get(main_endpoint)
    print(f"Main analyses endpoint: Status {response.status_code}")
except Exception as e:
    print(f"Main endpoint error: {e}")

# Test with query parameters
try:
    endpoint_with_params = f"{API_BASE}/analyses/trends/historical?days_back=14"
    response = requests.get(endpoint_with_params)
    print(f"With params: Status {response.status_code}")
    if response.status_code != 403:
        print(f"Response: {response.text}")
except Exception as e:
    print(f"With params error: {e}")