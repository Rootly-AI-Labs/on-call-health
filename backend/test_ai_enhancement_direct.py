#!/usr/bin/env python3
"""
Test AI enhancement directly
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_burnout_analyzer import get_ai_burnout_analyzer

async def test_ai_enhancement():
    print("🧪 Testing AI Enhancement Direct")
    
    # Mock analysis result structure
    mock_analysis_result = {
        "team_analysis": {
            "members": [
                {
                    "user_id": "test_user",
                    "user_name": "Test User",
                    "burnout_score": 5.5,
                    "risk_level": "medium",
                    "incident_count": 10,
                    "factors": {
                        "workload": 0.7,
                        "after_hours": 0.8,
                        "weekend_work": 0.2,
                        "incident_load": 0.6,
                        "response_time": 0.3
                    }
                }
            ]
        }
    }
    
    available_integrations = ["github", "slack"]
    
    try:
        # Test AI analyzer initialization
        ai_analyzer = get_ai_burnout_analyzer()
        print(f"✅ AI Analyzer initialized: available={ai_analyzer.available}")
        
        if not ai_analyzer.available:
            print("❌ AI Analyzer not available")
            return
        
        # Test member enhancement
        member_data = {
            "user_name": "Test User",
            "user_id": "test_user",
            "incidents": [],
            "github_activity": None,
            "slack_activity": None
        }
        
        traditional_analysis = mock_analysis_result["team_analysis"]["members"][0]
        
        enhanced_member = ai_analyzer.enhance_member_analysis(
            member_data,
            traditional_analysis,
            available_integrations
        )
        
        print(f"✅ Member enhancement completed")
        print(f"   Has AI insights: {'ai_insights' in enhanced_member}")
        print(f"   Has AI risk assessment: {'ai_risk_assessment' in enhanced_member}")
        
        # Test team insights
        team_insights = ai_analyzer.generate_team_insights(
            [enhanced_member],
            available_integrations
        )
        
        print(f"✅ Team insights generated: available={team_insights.get('available', False)}")
        
        if team_insights.get('available'):
            insights = team_insights.get('insights', {})
            print(f"   Team size: {insights.get('team_size', 0)}")
            print(f"   Risk distribution: {bool(insights.get('risk_distribution'))}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ai_enhancement())