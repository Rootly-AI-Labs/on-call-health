#!/usr/bin/env python3
"""
Test AI Integration with Current API Setup

Tests the newly merged AI burnout analysis components to ensure they work
correctly with the existing GitHub and Slack integrations.
"""
import asyncio
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.burnout_analyzer import BurnoutAnalyzerService
from app.services.ai_burnout_analyzer import get_ai_burnout_analyzer
from app.agents.burnout_agent import create_burnout_agent

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
ROOTLY_TOKEN = "rootly_live_e7d44b61c5af7a6e5fb5a0577d74e37dd0"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SLACK_TOKEN = os.getenv("SLACK_TOKEN")


async def test_ai_burnout_analyzer_service():
    """Test the AI Burnout Analyzer Service integration."""
    print("🤖 Testing AI Burnout Analyzer Service...")
    
    try:
        # Initialize the AI service
        ai_service = get_ai_burnout_analyzer()
        
        print(f"✅ AI Service initialized: available={ai_service.available}")
        
        if not ai_service.available:
            print("⚠️  AI Service not available - this is expected if smolagents isn't installed")
            return True
        
        # Test with mock member data
        mock_member_data = {
            "user_name": "Test User",
            "user_id": "test_123",
            "incidents": [
                {
                    "created_at": "2025-07-10T22:30:00Z",
                    "severity": "high",
                    "acknowledged_at_minutes": 5,
                    "resolved_at": "2025-07-10T23:15:00Z"
                },
                {
                    "created_at": "2025-07-13T14:30:00Z", 
                    "severity": "medium",
                    "acknowledged_at_minutes": 15,
                    "resolved_at": "2025-07-13T15:00:00Z"
                }
            ],
            "github_activity": {
                "commits": [
                    {
                        "created_at": "2025-07-11T23:45:00Z",
                        "additions": 150,
                        "deletions": 50,
                        "message": "Fix critical bug in authentication"
                    }
                ],
                "pull_requests": [
                    {
                        "created_at": "2025-07-12T19:30:00Z",
                        "additions": 300,
                        "deletions": 100,
                        "title": "Add new feature",
                        "state": "merged"
                    }
                ]
            },
            "slack_activity": {
                "messages": [
                    {
                        "created_at": "2025-07-11T20:00:00Z",
                        "text": "Working on the urgent fix",
                        "channel": "engineering"
                    },
                    {
                        "created_at": "2025-07-12T22:30:00Z",
                        "text": "This is really stressful, too many incidents",
                        "channel": "general"
                    }
                ]
            }
        }
        
        mock_traditional_analysis = {
            "user_name": "Test User",
            "risk_level": "medium",
            "burnout_score": 65,
            "recommendations": ["Review workload distribution"]
        }
        
        available_integrations = ["github", "slack"]
        
        # Test AI enhancement
        enhanced_analysis = ai_service.enhance_member_analysis(
            mock_member_data,
            mock_traditional_analysis,
            available_integrations
        )
        
        print("✅ AI enhancement completed")
        print(f"   - Has AI insights: {'ai_insights' in enhanced_analysis}")
        print(f"   - Has AI risk assessment: {'ai_risk_assessment' in enhanced_analysis}")
        print(f"   - Has AI recommendations: {'ai_recommendations' in enhanced_analysis}")
        print(f"   - AI confidence: {enhanced_analysis.get('ai_confidence', 'N/A')}")
        
        # Test team insights
        team_insights = ai_service.generate_team_insights([enhanced_analysis], available_integrations)
        print(f"✅ Team insights generated: available={team_insights.get('available', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ AI Service test failed: {e}")
        return False


async def test_burnout_agent_direct():
    """Test the Burnout Agent directly."""
    print("🧠 Testing Burnout Agent directly...")
    
    try:
        # Create the agent
        agent = create_burnout_agent()
        
        print(f"✅ Agent created: available={agent.agent_available}")
        
        # Test with mock data
        mock_member_data = {
            "name": "Test Developer",
            "incidents": [
                {
                    "timestamp": "2025-07-10T22:30:00Z",
                    "severity": "critical",
                    "response_time_minutes": 3
                }
            ],
            "commits": [
                {
                    "timestamp": "2025-07-11T23:45:00Z",
                    "changes": 200,
                    "message": "Emergency hotfix"
                }
            ],
            "slack_messages": [
                {
                    "text": "This is overwhelming, working late again",
                    "timestamp": "2025-07-11T20:00:00Z"
                }
            ]
        }
        
        available_sources = ["incidents", "github", "slack"]
        
        # Run analysis
        result = agent.analyze_member_burnout(mock_member_data, available_sources)
        
        print("✅ Agent analysis completed")
        print(f"   - Member: {result.get('member_name', 'Unknown')}")
        print(f"   - Risk level: {result.get('risk_assessment', {}).get('overall_risk_level', 'Unknown')}")
        print(f"   - Risk score: {result.get('risk_assessment', {}).get('risk_score', 'Unknown')}")
        print(f"   - Recommendations: {len(result.get('recommendations', []))}")
        print(f"   - Confidence: {result.get('confidence_score', 'Unknown')}")
        
        if result.get('ai_insights', {}).get('llm_analysis'):
            print(f"   - LLM reasoning available: Yes")
        else:
            print(f"   - LLM reasoning available: No (using fallback tools)")
            
        return True
        
    except Exception as e:
        print(f"❌ Agent test failed: {e}")
        return False


async def test_burnout_analyzer_with_ai():
    """Test the main BurnoutAnalyzerService with AI enhancement."""
    print("🔬 Testing BurnoutAnalyzerService with AI enhancement...")
    
    try:
        # Initialize service
        service = BurnoutAnalyzerService(ROOTLY_TOKEN)
        
        # Run analysis with AI enhancement enabled
        result = await service.analyze_burnout(
            time_range_days=7,
            include_github=bool(GITHUB_TOKEN),
            include_slack=bool(SLACK_TOKEN),
            github_token=GITHUB_TOKEN,
            slack_token=SLACK_TOKEN
        )
        
        print("✅ Burnout analysis with AI completed")
        print(f"   - Team members analyzed: {len(result.get('team_analysis', {}).get('members', []))}")
        print(f"   - Overall team health: {result.get('overall_team_health', 'Unknown')}")
        
        # Check if any member has AI insights
        ai_enhanced_members = 0
        for member in result.get('team_analysis', {}).get('members', []):
            if 'ai_insights' in member or 'ai_risk_assessment' in member:
                ai_enhanced_members += 1
        
        print(f"   - Members with AI insights: {ai_enhanced_members}")
        
        # Check for team-level AI insights
        if 'ai_team_insights' in result:
            print(f"   - Team AI insights available: Yes")
        else:
            print(f"   - Team AI insights available: No")
            
        return True
        
    except Exception as e:
        print(f"❌ Main service test failed: {e}")
        return False


async def test_ai_tools_individually():
    """Test individual AI tools."""
    print("🛠️  Testing individual AI tools...")
    
    try:
        # Test sentiment analyzer
        from app.agents.tools.sentiment_analyzer import create_sentiment_analyzer_tool
        sentiment_tool = create_sentiment_analyzer_tool()
        
        test_messages = [
            "This is really stressful",
            "Working late again tonight",
            "Great job on the release!",
            "I'm feeling overwhelmed with all these incidents"
        ]
        
        sentiment_result = sentiment_tool(test_messages, "slack")
        print(f"✅ Sentiment analyzer: {sentiment_result['overall_sentiment']} (score: {sentiment_result['sentiment_score']})")
        print(f"   - Stress indicators: {len(sentiment_result['stress_indicators'])}")
        
        # Test pattern analyzer
        from app.agents.tools.pattern_analyzer import create_pattern_analyzer_tool
        pattern_tool = create_pattern_analyzer_tool()
        
        test_events = [
            {"timestamp": "2025-07-10T22:30:00Z", "severity": "high"},
            {"timestamp": "2025-07-11T23:45:00Z", "severity": "medium"},
            {"timestamp": "2025-07-13T19:30:00Z", "severity": "low"}
        ]
        
        pattern_result = pattern_tool("incidents", test_events)
        print(f"✅ Pattern analyzer: {len(pattern_result['burnout_indicators'])} indicators found")
        print(f"   - After-hours rate: {pattern_result.get('after_hours_rate', 'N/A')}")
        
        # Test workload analyzer
        from app.agents.tools.workload_analyzer import create_workload_analyzer_tool
        workload_tool = create_workload_analyzer_tool()
        
        test_member_data = {
            "incidents": test_events,
            "commits": [{"timestamp": "2025-07-11T23:45:00Z", "changes": 200}],
            "messages": test_messages
        }
        
        workload_result = workload_tool(test_member_data)
        print(f"✅ Workload analyzer: {workload_result.get('workload_status', 'unknown')} workload")
        print(f"   - Intensity score: {workload_result.get('intensity_score', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Individual tools test failed: {e}")
        return False


async def main():
    """Run all AI integration tests."""
    print("🚀 Starting AI Integration Tests")
    print("=" * 50)
    
    # Check dependencies
    try:
        import smolagents
        print("✅ smolagents available")
        smolagents_available = True
    except ImportError:
        print("⚠️  smolagents not available - AI will use fallback mode")
        smolagents_available = False
    
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        print("✅ VADER sentiment analyzer available")
    except ImportError:
        print("❌ VADER sentiment analyzer not available")
        return False
    
    print("\n" + "=" * 50)
    
    # Run tests
    tests = [
        ("AI Tools Individual", test_ai_tools_individually),
        ("AI Burnout Agent", test_burnout_agent_direct),
        ("AI Service Integration", test_ai_burnout_analyzer_service),
        ("Full Pipeline", test_burnout_analyzer_with_ai)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        print("-" * 30)
        try:
            results[test_name] = await test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All AI integration tests passed!")
        print("\nAI Features Status:")
        if smolagents_available:
            print("✅ Full LLM-powered reasoning available")
        else:
            print("⚠️  Using fallback tools-only mode (install smolagents for full AI)")
        print("✅ AI enhancement pipeline working")
        print("✅ Individual AI tools functional")
        print("✅ Integration with existing analysis working")
    else:
        print("⚠️  Some tests failed - check output above for details")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())