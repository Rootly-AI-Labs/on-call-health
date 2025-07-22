#!/usr/bin/env python3
"""
Debug AI enhancement pipeline
"""
import asyncio
import sys
import os
import logging
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.ai_burnout_analyzer import get_ai_burnout_analyzer

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_ai_pipeline():
    print("🔍 Debugging AI Enhancement Pipeline")
    
    # Test AI analyzer availability
    try:
        ai_analyzer = get_ai_burnout_analyzer()
        print(f"✅ AI Analyzer initialized: available={ai_analyzer.available}")
        
        if not ai_analyzer.available:
            print("❌ AI Analyzer not available - this would cause AI enhancement to be skipped")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize AI analyzer: {e}")
        return False
    
    # Mock analysis structure that should match actual burnout analyzer output
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
    
    # Test enhancement pipeline like burnout_analyzer does
    try:
        enhanced_members = []
        original_members = mock_analysis_result.get("team_analysis", {}).get("members", [])
        print(f"📊 Processing {len(original_members)} members")
        
        for member in original_members:
            # Prepare member data for AI analysis
            member_data = {
                "user_id": member.get("user_id"),
                "user_name": member.get("user_name"), 
                "incidents": [],  # Simplified
                "github_activity": member.get("github_activity"),
                "slack_activity": member.get("slack_activity")
            }
            
            print(f"🔄 Enhancing member: {member_data['user_name']}")
            
            # Get AI enhancement
            enhanced_member = ai_analyzer.enhance_member_analysis(
                member_data,
                member,  # Traditional analysis
                available_integrations
            )
            
            print(f"✅ Member enhanced - has AI insights: {'ai_insights' in enhanced_member}")
            enhanced_members.append(enhanced_member)
        
        # Generate team-level AI insights
        print("🔄 Generating team insights")
        team_insights = ai_analyzer.generate_team_insights(
            enhanced_members,
            available_integrations
        )
        
        print(f"✅ Team insights generated: available={team_insights.get('available', False)}")
        
        if team_insights.get("available"):
            mock_analysis_result["ai_team_insights"] = team_insights
        
        # Add AI metadata
        mock_analysis_result["ai_enhanced"] = True
        
        print(f"\n🎉 AI Enhancement Complete:")
        print(f"   Members enhanced: {len(enhanced_members)}")
        print(f"   Team insights available: {mock_analysis_result.get('ai_team_insights', {}).get('available', False)}")
        print(f"   Analysis marked as ai_enhanced: {mock_analysis_result.get('ai_enhanced', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Enhancement failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ai_pipeline())
    print(f"\n{'✅' if success else '❌'} AI Pipeline Test {'PASSED' if success else 'FAILED'}")