#!/usr/bin/env python3
"""
Test analysis with AI enhancement
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.api.endpoints.analysis import run_analysis_task
from app.models import User
from app.services.ai_burnout_analyzer import set_user_context

class MockUser:
    def __init__(self):
        self.id = 2
        self.llm_token = "sk-ant-api03-test-token"
        self.llm_provider = "anthropic"

async def test_analysis_with_ai():
    print("🧪 Testing Analysis with AI Enhancement")
    
    # Mock user with LLM token
    user = MockUser()
    print(f"User ID: {user.id}, Provider: {user.llm_provider}")
    
    # This would be called by the API endpoint
    try:
        await run_analysis_task(
            analysis_id=999,  # Mock analysis ID
            rootly_token="test-token",
            days_back=30,
            user_id=user.id
        )
        print("✅ Analysis completed")
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_analysis_with_ai())