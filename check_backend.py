#!/usr/bin/env python3
import requests
import json

print("Checking backend status...\n")

# Test health endpoint
try:
    response = requests.get("http://localhost:8000/health", timeout=2)
    if response.status_code == 200:
        print("✅ Backend is running!")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"❌ Backend returned status code: {response.status_code}")
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to backend on http://localhost:8000")
    print("The backend server is not running.")
except Exception as e:
    print(f"❌ Error: {e}")

print("\nTo start the backend:")
print("1. cd /Users/spencercheng/Workspace/Rootly/rootly-burnout-detector-web/backend")
print("2. source venv/bin/activate")
print("3. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")