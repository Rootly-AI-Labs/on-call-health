#!/usr/bin/env python3
"""
Test direct analysis with AI enhancement
"""
import asyncio
import sys
import os
import sqlite3
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.burnout_analyzer import BurnoutAnalyzerService
from app.services.ai_burnout_analyzer import set_user_context

class MockUser:
    def __init__(self):
        self.id = 2
        self.llm_token = "sk-ant-api03-test-token"
        self.llm_provider = "anthropic"

async def test_direct_analysis():
    print("🧪 Testing Direct Analysis with AI Enhancement")
    
    # Set user context for AI analysis
    user = MockUser()
    set_user_context(user)
    print(f"✅ User context set: {user.llm_provider}")
    
    # Use a dummy Rootly token (analysis should use fallback data)
    analyzer = BurnoutAnalyzerService("dummy-token")
    
    try:
        # Run analysis with AI enhancement
        print("🔄 Running analysis...")
        results = await analyzer.analyze_burnout(
            time_range_days=30,
            include_weekends=True,
            include_github=False,
            include_slack=False
        )
        
        print("✅ Analysis completed")
        
        # Check for AI enhancement
        ai_enhanced = results.get("ai_enhanced", False)
        ai_team_insights = results.get("ai_team_insights", {})
        
        print(f"\n🤖 AI Enhancement Results:")
        print(f"   AI Enhanced: {ai_enhanced}")
        print(f"   AI Team Insights Available: {ai_team_insights.get('available', False)}")
        
        # Check members for AI insights
        team_analysis = results.get("team_analysis", {})
        members = team_analysis.get("members", [])
        
        ai_enhanced_members = 0
        for member in members:
            if 'ai_insights' in member or 'ai_risk_assessment' in member:
                ai_enhanced_members += 1
        
        print(f"   Total Members: {len(members)}")
        print(f"   AI-Enhanced Members: {ai_enhanced_members}")
        
        # Save result for inspection
        with open('direct_analysis_result.json', 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"   Results saved to direct_analysis_result.json")
        
        return ai_enhanced
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_analysis())
    print(f"\n{'✅' if success else '❌'} Direct Analysis {'PASSED' if success else 'FAILED'}")