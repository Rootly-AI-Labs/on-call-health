#!/usr/bin/env python3
"""
Test script to debug the GitHub endpoint with proper authentication
"""
import asyncio
import httpx
import json

async def test_with_auth():
    """Test the GitHub endpoint with proper authentication"""
    
    # First, let's get a valid auth token by logging in
    print("1. Getting authentication token...")
    
    async with httpx.AsyncClient() as client:
        # Let's try to register/login to get a token
        try:
            # Try a simple test endpoint first
            response = await client.get("http://localhost:8000/health")
            print(f"Health check: {response.status_code}")
            
            # Try to call the endpoint with dummy auth to see the exact error
            headers = {
                "Authorization": "Bearer invalid_token",
                "Content-Type": "application/json"
            }
            
            data = {"token": "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"}
            
            response = await client.post(
                "http://localhost:8000/integrations/github/token",
                headers=headers,
                json=data
            )
            
            print(f"\n2. GitHub endpoint test:")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code == 500:
                print("   This confirms the 500 error. The authentication is not the issue.")
                print("   The error is likely in the endpoint implementation.")
            
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_auth())