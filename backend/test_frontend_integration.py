#!/usr/bin/env python3
"""
Test the AI integration with frontend data format expectations
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

os.environ['ANTHROPIC_API_KEY'] = "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"

def test_frontend_data_format():
    """Test that AI analysis produces data in frontend-expected format."""
    
    print("🧪 Testing AI analysis data format for frontend...")
    
    try:
        from app.services.ai_burnout_analyzer import AIBurnoutAnalyzerService
        
        # Create AI analyzer
        ai_service = AIBurnoutAnalyzerService()
        print(f"✅ AI Service initialized: {ai_service.available}")
        
        if not ai_service.available:
            print("❌ AI service not available - skipping test")
            return
        
        # Create mock member data
        now = datetime.utcnow()
        
        member_data = {
            "user_id": "test-user-123", 
            "user_name": "Alex Johnson",
            "user_email": "alex@company.com",
            "incidents": [
                {
                    "created_at": (now - timedelta(days=i, hours=20)).isoformat(),
                    "severity": "high" if i < 3 else "medium",
                    "acknowledged_at_minutes": 3 if i < 3 else 8,
                    "resolved_at": (now - timedelta(days=i, hours=19)).isoformat(),
                    "urgency": "urgent" if i < 2 else "normal"
                }
                for i in range(8)
            ],
            "github_activity": {
                "commits": [
                    {
                        "created_at": (now - timedelta(days=i, hours=23)).isoformat(),
                        "sha": f"abc123{i}",
                        "message": f"Fix issue {i}",
                        "stats": {"additions": 50, "deletions": 10}
                    }
                    for i in range(15)
                ],
                "pull_requests": [
                    {
                        "created_at": (now - timedelta(days=2)).isoformat(),
                        "title": "Emergency hotfix",
                        "additions": 120,
                        "deletions": 30,
                        "state": "merged"
                    }
                ]
            },
            "slack_activity": {
                "messages": [
                    {
                        "timestamp": (now - timedelta(days=i, hours=19)).isoformat(),
                        "text": msg,
                        "channel": "engineering"
                    }
                    for i, msg in enumerate([
                        "This is getting overwhelming",
                        "Working late again tonight", 
                        "So many fires to put out",
                        "Really tired from all these incidents",
                        "Good work on the release!",
                        "Can't seem to catch a break"
                    ])
                ]
            }
        }
        
        # Mock traditional analysis
        traditional_analysis = {
            "user_id": "test-user-123",
            "user_name": "Alex Johnson", 
            "user_email": "alex@company.com",
            "burnout_score": 7.2,
            "risk_level": "medium",
            "incident_count": 8,
            "factors": {
                "workload": 8.5,
                "after_hours": 9.0,
                "weekend_work": 6.0,
                "incident_load": 8.0,
                "response_time": 7.5
            },
            "recommendations": [
                "Reduce after-hours incident response",
                "Consider workload redistribution"
            ]
        }
        
        available_integrations = ["incidents", "github", "slack"]
        
        print("🔍 Running AI enhancement...")
        
        # Get AI enhancement
        enhanced_analysis = ai_service.enhance_member_analysis(
            member_data,
            traditional_analysis,
            available_integrations
        )
        
        print("\n📊 Enhanced Analysis Structure:")
        print(f"Risk Level: {enhanced_analysis.get('risk_level')}")
        print(f"Burnout Score: {enhanced_analysis.get('burnout_score')}")
        
        # Check frontend-expected fields
        expected_ai_fields = [
            'ai_insights',
            'ai_risk_assessment', 
            'ai_recommendations',
            'ai_confidence',
            'ai_data_sources'
        ]
        
        print("\n🔍 Checking Frontend-Expected Fields:")
        for field in expected_ai_fields:
            if field in enhanced_analysis:
                print(f"✅ {field}: Present")
                
                # Show structure for key fields
                if field == 'ai_insights':
                    ai_insights = enhanced_analysis[field]
                    if 'llm_analysis' in ai_insights:
                        print(f"   • LLM Analysis: {len(ai_insights['llm_analysis'])} characters")
                    if 'analysis_method' in ai_insights:
                        print(f"   • Analysis Method: {ai_insights['analysis_method']}")
                        
                elif field == 'ai_risk_assessment':
                    risk_assessment = enhanced_analysis[field]
                    print(f"   • Risk Level: {risk_assessment.get('overall_risk_level')}")
                    print(f"   • Risk Score: {risk_assessment.get('risk_score')}")
                    print(f"   • Risk Factors: {len(risk_assessment.get('risk_factors', []))}")
                    
                elif field == 'ai_recommendations':
                    recommendations = enhanced_analysis[field]
                    print(f"   • Count: {len(recommendations)}")
                    if recommendations:
                        print(f"   • Sample: {recommendations[0].get('title', 'N/A')}")
                        
                elif field == 'ai_confidence':
                    confidence = enhanced_analysis[field]
                    print(f"   • Value: {confidence:.1%}")
                    
            else:
                print(f"❌ {field}: Missing")
        
        # Check if data structure matches frontend expectations
        print("\n🎯 Frontend Compatibility Check:")
        
        # Test AI insights structure
        ai_insights = enhanced_analysis.get('ai_insights', {})
        if 'llm_analysis' in ai_insights and isinstance(ai_insights['llm_analysis'], str):
            print("✅ LLM analysis text ready for display")
        else:
            print("❌ LLM analysis not in expected format")
            
        # Test risk assessment structure  
        ai_risk = enhanced_analysis.get('ai_risk_assessment', {})
        if all(key in ai_risk for key in ['overall_risk_level', 'risk_score', 'risk_factors']):
            print("✅ Risk assessment structure compatible")
        else:
            print("❌ Risk assessment structure incomplete")
            
        # Test recommendations structure
        ai_recs = enhanced_analysis.get('ai_recommendations', [])
        if ai_recs and all('title' in rec and 'description' in rec and 'priority' in rec for rec in ai_recs):
            print("✅ Recommendations structure compatible")
        else:
            print("❌ Recommendations structure incompatible")
            
        # Test team insights
        print("\n🏆 Testing Team Insights...")
        team_insights = ai_service.generate_team_insights([enhanced_analysis], available_integrations)
        
        if team_insights.get('available'):
            print("✅ Team insights generation successful")
            insights_data = team_insights.get('insights', {})
            print(f"   • Risk Distribution: {insights_data.get('risk_distribution', {}).get('distribution', {})}")
            print(f"   • Common Patterns: {len(insights_data.get('common_patterns', []))}")
        else:
            print("❌ Team insights generation failed")
            
        print("\n🎉 Integration test completed!")
        print(f"✅ AI Analysis: {'Working' if 'ai_insights' in enhanced_analysis else 'Failed'}")
        print(f"✅ Frontend Format: {'Compatible' if all(field in enhanced_analysis for field in expected_ai_fields[:3]) else 'Incompatible'}")
        print(f"✅ LLM Reasoning: {'Available' if ai_insights.get('llm_analysis') else 'Fallback mode'}")
        
        return enhanced_analysis
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_frontend_data_format()