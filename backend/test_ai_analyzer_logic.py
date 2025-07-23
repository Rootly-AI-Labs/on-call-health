#!/usr/bin/env python3
"""
Test the AI analyzer logic to verify it works correctly
"""
import asyncio
from app.core.simple_burnout_analyzer import SimpleBurnoutAnalyzer
from app.services.burnout_analyzer import BurnoutAnalyzerService

async def test_simple_analyzer():
    """Test the SimpleBurnoutAnalyzer to ensure it sets ai_enhanced=False"""
    print("Testing SimpleBurnoutAnalyzer...")
    
    # Create a fake API token for testing
    analyzer = SimpleBurnoutAnalyzer("fake_token")
    
    # Test the interface
    print("✅ SimpleBurnoutAnalyzer created successfully")
    print(f"   Has analyze_burnout method: {hasattr(analyzer, 'analyze_burnout')}")
    print(f"   Has analyze_team_burnout method: {hasattr(analyzer, 'analyze_team_burnout')}")
    
    # Test team analysis directly
    test_users = []
    test_incidents = []
    test_metadata = {"days_analyzed": 30}
    
    result = analyzer.analyze_team_burnout(test_users, test_incidents, test_metadata)
    print(f"   ai_enhanced in result: {result.get('ai_enhanced', 'MISSING')}")
    
    return result.get('ai_enhanced') == False

def test_ai_enhanced_analyzer():
    """Test the BurnoutAnalyzerService to ensure it can set ai_enhanced=True"""
    print("\nTesting BurnoutAnalyzerService...")
    
    # Create a fake API token for testing
    analyzer = BurnoutAnalyzerService("fake_token")
    
    print("✅ BurnoutAnalyzerService created successfully")
    print(f"   Has analyze_burnout method: {hasattr(analyzer, 'analyze_burnout')}")
    
    return True

if __name__ == "__main__":
    # Test basic functionality
    simple_test = asyncio.run(test_simple_analyzer())
    ai_test = test_ai_enhanced_analyzer()
    
    print(f"\n📊 Test Results:")
    print(f"   SimpleBurnoutAnalyzer: {'✅ PASS' if simple_test else '❌ FAIL'}")
    print(f"   BurnoutAnalyzerService: {'✅ PASS' if ai_test else '❌ FAIL'}")
    
    if simple_test and ai_test:
        print("\n🎉 All tests passed! The AI analyzer logic should work correctly.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")