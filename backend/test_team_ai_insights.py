#!/usr/bin/env python3
"""
Test team AI insights integration
"""
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

os.environ['ANTHROPIC_API_KEY'] = "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"

def test_team_ai_insights():
    """Test team-level AI insights generation."""
    
    print("🏆 Testing Team AI Insights Integration...")
    
    try:
        from app.services.ai_burnout_analyzer import AIBurnoutAnalyzerService
        
        # Create AI analyzer
        ai_service = AIBurnoutAnalyzerService()
        print(f"✅ AI Service initialized: {ai_service.available}")
        
        if not ai_service.available:
            print("❌ AI service not available - skipping test")
            return
        
        # Create mock team data with multiple members showing different patterns
        now = datetime.utcnow()
        
        # Member 1: High after-hours work
        member1 = {
            "user_name": "Alex Johnson",
            "risk_level": "high",
            "burnout_score": 8.2,
            "ai_insights": {
                "analysis_method": "llm_powered_reasoning",
                "llm_analysis": "Shows excessive after-hours work patterns with high incident response load"
            },
            "ai_risk_assessment": {
                "overall_risk_level": "high",
                "risk_score": 85,
                "risk_factors": [
                    "High after-hours incident response: 90.0%",
                    "Excessive workload intensity: 8.5/10",
                    "Negative communication sentiment detected"
                ],
                "protective_factors": ["Strong technical skills", "Good team collaboration"]
            },
            "ai_recommendations": [
                {
                    "priority": "urgent",
                    "category": "workload_management",
                    "title": "Immediate Workload Reduction",
                    "description": "Critical burnout risk detected - immediate intervention needed"
                }
            ]
        }
        
        # Member 2: Medium risk with weekend work
        member2 = {
            "user_name": "Sarah Chen", 
            "risk_level": "medium",
            "burnout_score": 6.1,
            "ai_insights": {
                "analysis_method": "direct_tool_analysis",
                "llm_analysis": "Moderate burnout risk with concerning weekend work patterns"
            },
            "ai_risk_assessment": {
                "overall_risk_level": "medium",
                "risk_score": 61,
                "risk_factors": [
                    "High weekend work: 35.0%",
                    "Moderate workload concerns"
                ],
                "protective_factors": ["Balanced communication tone", "Good work-life boundaries weekdays"]
            },
            "ai_recommendations": [
                {
                    "priority": "medium",
                    "category": "work_life_balance",
                    "title": "Weekend Work Optimization",
                    "description": "Reduce weekend commitments for better recovery"
                }
            ]
        }
        
        # Member 3: Low risk but AI escalated due to sentiment
        member3 = {
            "user_name": "Mike Torres",
            "risk_level": "medium", # AI escalated from low
            "burnout_score": 4.2,
            "risk_escalated_by_ai": True,
            "ai_insights": {
                "analysis_method": "llm_powered_reasoning", 
                "llm_analysis": "AI detected concerning communication patterns despite low traditional metrics"
            },
            "ai_risk_assessment": {
                "overall_risk_level": "medium",
                "risk_score": 55,
                "risk_factors": [
                    "Slack: Negative communication sentiment",
                    "Slack: High after-hours communication: 45.0%"
                ],
                "protective_factors": ["Low incident load", "Sustainable workload levels"]
            },
            "ai_recommendations": [
                {
                    "priority": "medium",
                    "category": "communication_health", 
                    "title": "Communication Support",
                    "description": "Negative sentiment patterns detected in team communications"
                }
            ]
        }
        
        team_members = [member1, member2, member3]
        available_integrations = ["incidents", "github", "slack"]
        
        print("🔍 Generating team AI insights...")
        
        # Generate team insights
        team_insights_result = ai_service.generate_team_insights(team_members, available_integrations)
        
        print("\n📊 Team AI Insights Results:")
        if team_insights_result.get('available'):
            insights = team_insights_result['insights']
            
            print(f"✅ Team Size: {insights['team_size']}")
            print(f"✅ Data Sources: {', '.join(insights['data_sources'])}")
            
            # Risk Distribution
            risk_dist = insights['risk_distribution']
            print(f"✅ Risk Distribution:")
            print(f"   • High Risk: {risk_dist['distribution'].get('high', 0)}")
            print(f"   • Medium Risk: {risk_dist['distribution'].get('medium', 0)}")
            print(f"   • Low Risk: {risk_dist['distribution'].get('low', 0)}")
            print(f"   • AI Escalations: {risk_dist['ai_escalations']}")
            
            # Common Patterns  
            patterns = insights['common_patterns']
            print(f"✅ Common Patterns ({len(patterns)} detected):")
            for pattern in patterns:
                print(f"   • {pattern['pattern']}: {pattern['affected_members']} members ({pattern['percentage']:.0f}%)")
            
            # Team Recommendations
            recommendations = insights['team_recommendations']
            print(f"✅ Team Recommendations ({len(recommendations)} generated):")
            for rec in recommendations[:2]:
                print(f"   • [{rec['priority'].upper()}] {rec['title']}")
                
            # Workload Distribution
            workload = insights['workload_distribution']
            print(f"✅ Workload Distribution:")
            print(f"   • Average Intensity: {workload['average_intensity']:.1f}")
            print(f"   • High Workload Members: {workload['high_workload_members']}")
            print(f"   • Balance: {workload['workload_balance']}")
            
            # LLM Team Analysis
            if 'llm_team_analysis' in insights:
                print(f"✅ LLM Team Analysis: {len(insights['llm_team_analysis'])} characters")
                print(f"   Preview: {insights['llm_team_analysis'][:150]}...")
            else:
                print("❌ No LLM team analysis generated")
                
            # Check frontend compatibility
            print("\n🎯 Frontend Compatibility Check:")
            required_fields = ['analysis_timestamp', 'team_size', 'data_sources', 'risk_distribution', 
                             'common_patterns', 'team_recommendations', 'workload_distribution']
            
            for field in required_fields:
                if field in insights:
                    print(f"✅ {field}: Present")
                else:
                    print(f"❌ {field}: Missing")
                    
            # Test data structure format
            print("\n📋 Data Structure Validation:")
            
            # Check risk distribution structure
            if all(key in risk_dist for key in ['distribution', 'high_risk_percentage', 'total_members']):
                print("✅ Risk distribution structure valid")
            else:
                print("❌ Risk distribution structure invalid")
                
            # Check pattern structure
            if patterns and all('pattern' in p and 'affected_members' in p and 'severity' in p for p in patterns):
                print("✅ Common patterns structure valid")
            else:
                print("❌ Common patterns structure invalid")
                
            # Check recommendations structure
            if recommendations and all('priority' in r and 'title' in r and 'description' in r for r in recommendations):
                print("✅ Team recommendations structure valid")
            else:
                print("❌ Team recommendations structure invalid")
                
        else:
            print("❌ Team insights generation failed")
            print(f"Error: {team_insights_result.get('error', 'Unknown error')}")
            
        print("\n🎉 Team AI insights test completed!")
        print(f"✅ Generation: {'Success' if team_insights_result.get('available') else 'Failed'}")
        print(f"✅ LLM Analysis: {'Available' if insights.get('llm_team_analysis') else 'Not generated'}")
        print(f"✅ Frontend Ready: {'Yes' if team_insights_result.get('available') else 'No'}")
        
        return team_insights_result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_team_ai_insights()