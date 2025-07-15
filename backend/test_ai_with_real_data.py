#!/usr/bin/env python3
"""
Quick test to verify AI works with real data analysis if tokens are available
"""
import asyncio
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.burnout_analyzer import BurnoutAnalyzerService

async def test_real_data():
    # Use working token from previous tests
    ROOTLY_TOKEN = "rootly_live_e7d44b61c5af7a6e5fb5a0577d74e37dd0"
    
    print("🔍 Testing AI with real Rootly data...")
    
    service = BurnoutAnalyzerService(ROOTLY_TOKEN)
    
    try:
        result = await service.analyze_burnout(
            time_range_days=30,
            include_github=False,  # Skip GitHub for this test
            include_slack=False    # Skip Slack for this test  
        )
        
        print(f"✅ Analysis completed successfully")
        
        team_members = result.get('team_analysis', {}).get('members', [])
        print(f"📊 Found {len(team_members)} team members")
        
        ai_enhanced_count = 0
        for member in team_members:
            if 'ai_insights' in member or 'ai_risk_assessment' in member:
                ai_enhanced_count += 1
                
        print(f"🤖 {ai_enhanced_count} members have AI insights")
        
        if 'ai_team_insights' in result:
            print("🧠 Team-level AI insights generated")
            team_insights = result['ai_team_insights']
            if team_insights.get('available'):
                insights_data = team_insights.get('insights', {})
                print(f"   - Risk distribution analyzed: {insights_data.get('risk_distribution', {}).get('total_members', 0)} members")
                print(f"   - Common patterns found: {len(insights_data.get('common_patterns', []))}")
                print(f"   - Team recommendations: {len(insights_data.get('team_recommendations', []))}")
        
        # Show a sample of AI analysis if available
        if team_members and ai_enhanced_count > 0:
            for member in team_members:
                if 'ai_risk_assessment' in member:
                    ai_risk = member['ai_risk_assessment']
                    print(f"\n👤 Sample AI analysis for {member.get('user_name', 'Unknown')}:")
                    print(f"   - AI Risk Level: {ai_risk.get('overall_risk_level', 'unknown')}")
                    print(f"   - AI Risk Score: {ai_risk.get('risk_score', 0)}")
                    print(f"   - Risk Factors: {len(ai_risk.get('risk_factors', []))}")
                    print(f"   - AI Recommendations: {len(member.get('ai_recommendations', []))}")
                    break
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_real_data())