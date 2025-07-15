#!/usr/bin/env python3
"""
Test script for LLM-powered reasoning with smolagents
"""
import sys
import os
from datetime import datetime, timedelta

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_llm_reasoning():
    """Test the LLM reasoning capabilities."""
    print("🤖 Testing LLM-Powered Burnout Analysis with Smolagents")
    print("=" * 60)
    
    # Check if OpenAI API key is available
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        print("\nTo test LLM reasoning, you need to:")
        print("1. Get an OpenAI API key from https://platform.openai.com/")
        print("2. Set it as an environment variable:")
        print("   export OPENAI_API_KEY='your-key-here'")
        print("3. Run this test again")
        print("\nFor now, the system will use direct tool analysis (which works great!)")
        return False
    
    print(f"✅ OpenAI API key detected: {api_key[:10]}...")
    
    try:
        from app.agents.burnout_agent import create_burnout_agent
        
        # Create agent with LLM reasoning
        print("\n🔧 Initializing agent with LLM reasoning...")
        agent = create_burnout_agent("gpt-4o-mini")
        
        if not agent.agent_available:
            print("❌ LLM agent not available, falling back to direct tool analysis")
            print("This is still intelligent analysis, just without natural language reasoning")
            return False
        
        print("✅ LLM agent initialized successfully!")
        
        # Create realistic test data
        print("\n📊 Creating test data for analysis...")
        member_data = {
            "name": "Sarah Chen",
            "user_id": "sarah_123",
            "incidents": [
                {
                    "timestamp": (datetime.now() - timedelta(hours=i*8 + 20)).isoformat(),  # Many after-hours
                    "severity": "critical" if i % 4 == 0 else "high",
                    "response_time_minutes": 3 + (i % 8),  # Very fast response pressure
                    "after_hours": i % 3 == 0,  # 1/3 after hours
                    "weekend": i % 7 == 0   # Some weekends
                }
                for i in range(25)  # High incident load
            ],
            "slack_messages": [
                "Working on the critical fix now",
                "This keeps breaking, getting frustrated", 
                "Another emergency deployment",
                "I'm tired of these production issues",
                "Can we please fix the monitoring?",
                "Working late again tonight",
                "This is the third incident today",
                "I need help with this workload"
            ],
            "github_activity": {
                "commits_count": 45,
                "pull_requests_count": 8,
                "after_hours_commits": 18,  # 40% after hours
                "weekend_commits": 8,
                "avg_pr_size": 250
            },
            "slack_activity": {
                "messages_sent": 120,
                "sentiment_score": -0.35,  # Negative sentiment
                "after_hours_messages": 35,
                "weekend_messages": 15
            }
        }
        
        # Run LLM-powered analysis
        print("\n🧠 Running LLM analysis with natural language reasoning...")
        print("The LLM will:")
        print("- Use our custom tools to analyze patterns")
        print("- Reason about the interconnections between data points")
        print("- Generate contextual insights and recommendations")
        print("- Explain the 'why' behind the patterns")
        
        result = agent.analyze_member_burnout(
            member_data,
            available_data_sources=["incidents", "github", "slack"]
        )
        
        print("\n" + "="*60)
        print("🎯 LLM ANALYSIS RESULTS")
        print("="*60)
        
        print(f"\n👤 Member: {result['member_name']}")
        print(f"⏰ Analysis Time: {result['analysis_timestamp']}")
        print(f"📊 Data Sources: {', '.join(result['data_sources_analyzed'])}")
        print(f"🎯 Analysis Type: {result.get('analysis_type', 'standard')}")
        
        # Show LLM reasoning
        ai_insights = result.get('ai_insights', {})
        if 'llm_analysis' in ai_insights:
            print(f"\n🧠 LLM REASONING:")
            print("-" * 40)
            llm_reasoning = ai_insights['llm_analysis']
            # Pretty print the LLM reasoning
            for line in llm_reasoning.split('\n'):
                if line.strip():
                    print(f"  {line.strip()}")
        
        # Show risk assessment
        risk_assessment = result.get('risk_assessment', {})
        print(f"\n🚨 RISK ASSESSMENT:")
        print(f"  Overall Risk: {risk_assessment.get('overall_risk_level', 'unknown').upper()}")
        print(f"  Risk Score: {risk_assessment.get('risk_score', 0)}/100")
        
        risk_factors = risk_assessment.get('risk_factors', [])
        if risk_factors:
            print(f"  Risk Factors:")
            for factor in risk_factors[:3]:
                print(f"    • {factor}")
        
        # Show recommendations
        recommendations = result.get('recommendations', [])
        if recommendations:
            print(f"\n💡 AI RECOMMENDATIONS:")
            for i, rec in enumerate(recommendations[:3], 1):
                print(f"  {i}. {rec.get('title', 'Recommendation')}")
                print(f"     Priority: {rec.get('priority', 'medium').upper()}")
                print(f"     {rec.get('description', '')}")
                if rec.get('actions'):
                    print(f"     Actions: {', '.join(rec['actions'][:2])}")
                print()
        
        print(f"🎯 Confidence: {result.get('confidence_score', 0):.1%}")
        
        print("\n" + "="*60)
        print("✅ LLM REASONING TEST COMPLETED SUCCESSFULLY!")
        print("="*60)
        
        print("\n🎉 What just happened:")
        print("- The LLM analyzed Sarah's complex work patterns")
        print("- It used our custom tools to examine incidents, code, and communication")
        print("- It reasoned about the interconnections and context")
        print("- It generated natural language insights explaining the 'why'")
        print("- It provided specific, actionable recommendations")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def demo_comparison():
    """Show the difference between direct tools and LLM reasoning."""
    print("\n" + "="*60)
    print("📋 COMPARISON: Direct Tools vs LLM Reasoning")
    print("="*60)
    
    print("\n🔧 DIRECT TOOLS (what we had before):")
    print("✓ Fast, deterministic analysis")
    print("✓ Rule-based pattern detection")
    print("✓ Statistical metrics calculation")
    print("✓ Template-based recommendations")
    print("❌ No contextual reasoning")
    print("❌ No natural language insights")
    
    print("\n🧠 LLM REASONING (what we have now):")
    print("✓ Everything from direct tools PLUS:")
    print("✓ Natural language understanding")
    print("✓ Contextual pattern interpretation")
    print("✓ Reasoning about cause and effect")
    print("✓ Personalized, narrative insights")
    print("✓ Adaptive analysis approach")
    print("✓ Human-like recommendation explanations")
    
    print("\n💡 EXAMPLE:")
    print("Direct Tools: 'High after-hours work detected: 40%'")
    print("LLM Reasoning: 'Sarah is working 40% of her time after hours, likely")
    print("              because she feels responsible for system stability.")
    print("              This pattern suggests she may need better support")
    print("              and clearer boundaries to prevent burnout.'")

if __name__ == "__main__":
    success = test_llm_reasoning()
    
    if success:
        print("\n🚀 NEXT STEPS:")
        print("1. Set your OPENAI_API_KEY to enable LLM reasoning")
        print("2. Run your burnout analysis - it will now use natural language insights!")
        print("3. Check the AI Insights section in member detail modals")
        print("4. Enjoy the enhanced contextual understanding! 🎯")
    else:
        print("\n📝 FALLBACK MODE:")
        print("- The system works great without an LLM key")
        print("- You're getting sophisticated analysis with custom tools")
        print("- Set OPENAI_API_KEY when you want natural language reasoning")
    
    # Always show the comparison
    demo_comparison()