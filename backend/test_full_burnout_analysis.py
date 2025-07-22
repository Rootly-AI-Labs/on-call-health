#!/usr/bin/env python3
"""
Test the complete burnout analysis with real data
"""
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

os.environ['ANTHROPIC_API_KEY'] = "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"

def test_burnout_analysis():
    """Test complete burnout analysis with mock data."""
    
    print("🧪 Testing full burnout analysis with LLM reasoning...")
    
    try:
        # Test smolagents import directly
        try:
            from smolagents import CodeAgent, LiteLLMModel
            print("✅ smolagents imports working")
        except Exception as e:
            print(f"❌ smolagents import failed: {e}")
        
        from app.agents.burnout_agent import BurnoutDetectionAgent
        
        # Enable detailed logging to see what's happening
        import logging
        logging.basicConfig(level=logging.DEBUG)
        
        # Create agent
        agent = BurnoutDetectionAgent("claude-3-haiku-20240307")
        print("✅ Created burnout detection agent")
        print(f"Agent available: {agent.agent_available}")
        
        if hasattr(agent, 'agent') and agent.agent:
            print("✅ LLM agent properly initialized")
        else:
            print("❌ LLM agent not initialized - using fallback")
        
        # Create mock member data with concerning patterns
        now = datetime.utcnow()
        
        # Generate mock incidents with after-hours and weekend patterns
        incidents = []
        for i in range(8):  # 8 incidents in 30 days - high load
            incident_time = now - timedelta(days=i*3, hours=20)  # After hours
            incidents.append({
                "id": f"inc-{i}",
                "title": f"Production issue {i}",
                "timestamp": incident_time.isoformat(),
                "severity": "high" if i < 3 else "medium",
                "response_time_minutes": 3 if i < 3 else 8,  # Fast response pressure
                "after_hours": True,
                "weekend": incident_time.weekday() >= 5
            })
        
        # Generate commits with late-night pattern
        commits = []
        for i in range(25):  # High commit frequency
            commit_time = now - timedelta(days=i, hours=23)  # Late night
            commits.append({
                "id": f"commit-{i}",
                "message": f"Fix critical issue {i}",
                "timestamp": commit_time.isoformat(),
                "changes": 600 if i < 5 else 200,  # Some large commits
                "after_hours": True
            })
        
        # Generate Slack messages with stress indicators
        messages = []
        stress_messages = [
            "This is getting overwhelming",
            "Working late again tonight",
            "So many fires to put out",
            "Really tired from all these incidents",
            "Can't seem to catch a break",
            "Pressure is really high this week"
        ]
        
        for i, msg in enumerate(stress_messages):
            msg_time = now - timedelta(days=i*2, hours=19)
            messages.append({
                "text": msg,
                "timestamp": msg_time.isoformat(),
                "channel": "engineering",
                "after_hours": True
            })
        
        # Add some normal messages too
        for i in range(15):
            msg_time = now - timedelta(days=i, hours=14)
            messages.append({
                "text": f"Working on feature {i}",
                "timestamp": msg_time.isoformat(),
                "channel": "engineering",
                "after_hours": False
            })
        
        member_data = {
            "name": "Alex Johnson",
            "incidents": incidents,
            "commits": commits,
            "pull_requests": [
                {
                    "id": "pr-1",
                    "title": "Emergency hotfix",
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "size": 1200,  # Large PR
                    "after_hours": True
                }
            ],
            "messages": messages,
            "slack_messages": messages,  # Same as messages for this test
            "github_activity": {
                "commits_count": len(commits),
                "pull_requests_count": 1,
                "after_hours_commits": sum(1 for c in commits if c.get("after_hours"))
            },
            "slack_activity": {
                "messages_sent": len(messages),
                "sentiment_score": -0.2,  # Negative sentiment
                "after_hours_messages": sum(1 for m in messages if m.get("after_hours"))
            }
        }
        
        available_data_sources = ["incidents", "github", "slack"]
        
        print("🔍 Running AI-powered burnout analysis...")
        
        # Run the analysis
        result = agent.analyze_member_burnout(
            member_data, 
            available_data_sources
        )
        
        print("\n📊 Analysis Results:")
        print(f"Member: {result.get('member_name')}")
        print(f"Risk Level: {result.get('risk_assessment', {}).get('overall_risk_level')}")
        print(f"Risk Score: {result.get('risk_assessment', {}).get('risk_score')}")
        print(f"Confidence: {result.get('confidence_score'):.1%}")
        
        # Check if we got LLM analysis
        ai_insights = result.get('ai_insights', {})
        if 'llm_analysis' in ai_insights:
            print(f"Analysis Method: LLM-powered reasoning ✅")
            print(f"\n🤖 AI Natural Language Analysis:")
            print(ai_insights['llm_analysis'][:300] + "..." if len(ai_insights['llm_analysis']) > 300 else ai_insights['llm_analysis'])
        else:
            print(f"Analysis Method: Direct tool analysis (fallback)")
        
        # Show risk factors
        risk_factors = result.get('risk_assessment', {}).get('risk_factors', [])
        if risk_factors:
            print(f"\n⚠️  Key Risk Factors:")
            for factor in risk_factors[:3]:
                print(f"  • {factor}")
        
        # Show recommendations
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n💡 Top Recommendations:")
            for rec in recommendations[:2]:
                print(f"  • {rec.get('title')}: {rec.get('description')}")
        
        print("\n🎉 Burnout analysis completed successfully!")
        print(f"✅ LLM reasoning: {'YES' if 'llm_analysis' in ai_insights else 'NO (fallback used)'}")
        print(f"✅ Risk detection: {'YES' if result.get('risk_assessment', {}).get('overall_risk_level') != 'low' else 'NO'}")
        print(f"✅ Recommendations: {'YES' if recommendations else 'NO'}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_burnout_analysis()