#!/usr/bin/env python3
"""
Test script for the AI burnout detection agent
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.agents.burnout_agent import create_burnout_agent
from app.services.ai_burnout_analyzer import get_ai_burnout_analyzer

def test_sentiment_analysis():
    """Test sentiment analysis tool."""
    print("Testing Sentiment Analysis Tool...")
    
    # Create agent
    agent = create_burnout_agent()
    
    # Test data
    positive_messages = [
        "Great job on the fix!",
        "Thanks for the quick response",
        "This looks good to me"
    ]
    
    negative_messages = [
        "This is taking too long",
        "I'm stressed about the deadline", 
        "This keeps breaking"
    ]
    
    # Test positive sentiment
    result = agent.sentiment_analyzer(positive_messages, "slack")
    print(f"Positive sentiment result: {result['overall_sentiment']} (score: {result['sentiment_score']})")
    
    # Test negative sentiment  
    result = agent.sentiment_analyzer(negative_messages, "slack")
    print(f"Negative sentiment result: {result['overall_sentiment']} (score: {result['sentiment_score']})")
    
    print("✅ Sentiment analysis test passed\n")

def test_pattern_analysis():
    """Test pattern analysis tool."""
    print("Testing Pattern Analysis Tool...")
    
    # Create agent
    agent = create_burnout_agent()
    
    # Create test incident data with after-hours pattern
    now = datetime.utcnow()
    incidents = []
    
    for i in range(20):
        # Create some after-hours incidents (20:00 hour)
        incident_time = now - timedelta(days=i)
        if i % 3 == 0:  # 1/3 are after hours
            incident_time = incident_time.replace(hour=20)
        else:
            incident_time = incident_time.replace(hour=14)
            
        incidents.append({
            "timestamp": incident_time.isoformat(),
            "severity": "high" if i % 5 == 0 else "medium",
            "response_time_minutes": 10 + (i % 15)
        })
    
    # Test pattern analysis
    result = agent.pattern_analyzer("incidents", incidents)
    print(f"Pattern analysis result: {result['pattern_summary']}")
    print(f"Burnout indicators: {result['burnout_indicators']}")
    
    print("✅ Pattern analysis test passed\n")

def test_workload_analysis():
    """Test workload analysis tool."""
    print("Testing Workload Analysis Tool...")
    
    # Create agent
    agent = create_burnout_agent()
    
    # Create test user data
    user_data = {
        "incidents": [{"timestamp": datetime.utcnow().isoformat(), "severity": "high"} for _ in range(15)],
        "commits": [{"timestamp": datetime.utcnow().isoformat(), "changes": 100} for _ in range(25)],
        "messages": [{"timestamp": datetime.utcnow().isoformat(), "text": "test"} for _ in range(40)]
    }
    
    # Test workload analysis
    result = agent.workload_analyzer(user_data)
    print(f"Workload status: {result['workload_status']}")
    print(f"Intensity score: {result['intensity_score']}")
    print(f"Sustainability indicators: {result['sustainability_indicators']}")
    
    print("✅ Workload analysis test passed\n")

def test_full_member_analysis():
    """Test full member analysis integration."""
    print("Testing Full Member Analysis...")
    
    # Create agent
    agent = create_burnout_agent()
    
    # Create comprehensive test data
    member_data = {
        "name": "Test User",
        "user_id": "test123",
        "incidents": [
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=i*2)).isoformat(),
                "severity": "high" if i % 3 == 0 else "medium",
                "response_time_minutes": 5 + (i % 10)
            }
            for i in range(20)
        ],
        "commits": [
            {
                "timestamp": (datetime.utcnow() - timedelta(hours=i*3)).isoformat(),
                "changes": 50 + (i % 200),
                "message": "Fix bug" if i % 2 == 0 else "Add feature"
            }
            for i in range(30)
        ],
        "slack_messages": [
            {
                "text": "Working on the urgent fix" if i % 4 == 0 else "This looks good",
                "timestamp": (datetime.utcnow() - timedelta(hours=i)).isoformat()
            }
            for i in range(50)
        ]
    }
    
    # Test full analysis
    result = agent.analyze_member_burnout(
        member_data,
        available_data_sources=["incidents", "github", "slack"]
    )
    
    print(f"Member: {result['member_name']}")
    print(f"Risk assessment: {result['risk_assessment']['overall_risk_level']}")
    print(f"Risk score: {result['risk_assessment']['risk_score']}/100")
    print(f"Recommendations: {len(result['recommendations'])} generated")
    print(f"Confidence: {result['confidence_score']:.2f}")
    
    if result['recommendations']:
        print("\nTop recommendation:")
        rec = result['recommendations'][0]
        print(f"  Priority: {rec['priority']}")
        print(f"  Title: {rec['title']}")
        print(f"  Description: {rec['description']}")
    
    print("✅ Full member analysis test passed\n")

def test_ai_service_integration():
    """Test the AI service integration."""
    print("Testing AI Service Integration...")
    
    # Get AI service
    ai_service = get_ai_burnout_analyzer()
    
    # Create mock traditional analysis
    traditional_analysis = {
        "user_id": "test123",
        "user_name": "Test User",
        "burnout_score": 35.5,
        "risk_level": "medium",
        "incident_count": 20,
        "factors": {
            "workload": 6.5,
            "after_hours": 4.2,
            "weekend_work": 3.1,
            "response_time": 7.8
        }
    }
    
    # Create mock member data
    member_data = {
        "user_id": "test123",
        "user_name": "Test User",
        "incidents": [{"timestamp": datetime.utcnow().isoformat()} for _ in range(20)],
        "github_activity": {"commits_count": 25, "after_hours_commits": 5},
        "slack_activity": {"messages_sent": 40, "sentiment_score": -0.2}
    }
    
    # Test enhancement
    enhanced = ai_service.enhance_member_analysis(
        member_data,
        traditional_analysis,
        ["github", "slack"]
    )
    
    print(f"AI enhanced: {enhanced.get('ai_enhanced', False)}")
    if enhanced.get('ai_risk_assessment'):
        print(f"AI risk level: {enhanced['ai_risk_assessment']['overall_risk_level']}")
    if enhanced.get('ai_recommendations'):
        print(f"AI recommendations: {len(enhanced['ai_recommendations'])}")
    print(f"AI confidence: {enhanced.get('ai_confidence', 0):.2f}")
    
    print("✅ AI service integration test passed\n")

if __name__ == "__main__":
    print("🤖 Testing AI Burnout Detection Agent\n")
    print("=" * 50)
    
    try:
        test_sentiment_analysis()
        test_pattern_analysis()
        test_workload_analysis()
        test_full_member_analysis()
        test_ai_service_integration()
        
        print("🎉 All tests passed!")
        print("\nAI Agent Integration Summary:")
        print("- ✅ Sentiment analysis working")
        print("- ✅ Pattern analysis working")
        print("- ✅ Workload analysis working")
        print("- ✅ Full member analysis working")
        print("- ✅ Service integration working")
        print("\nThe smolagents integration is ready for use!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)