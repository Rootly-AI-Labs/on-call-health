#!/usr/bin/env python3
"""
Debug script for GitHub integration endpoint
"""
import asyncio
import httpx
import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_github_endpoint():
    """Test the GitHub token validation directly"""
    print("Testing GitHub API with user's token...")
    
    # Test direct GitHub API
    headers = {
        'Authorization': 'token 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',
        'Accept': 'application/json'
    }
    
    async with httpx.AsyncClient() as client:
        try:
            # Test GitHub API directly
            print("1. Testing GitHub API directly...")
            response = await client.get('https://api.github.com/user', headers=headers)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                user_info = response.json()
                print(f"   Username: {user_info.get('login')}")
                print(f"   Public repos: {user_info.get('public_repos')}")
            else:
                print(f"   Error: {response.text}")
                return
            
            # Test our backend validation logic
            print("\n2. Testing backend token validation logic...")
            from app.api.endpoints.github import connect_github_with_token, TokenRequest
            from app.models import get_db, User
            
            # This will help us see what the actual error is
            print("   Imports successful")
            
        except Exception as e:
            print(f"Error during testing: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_github_endpoint())