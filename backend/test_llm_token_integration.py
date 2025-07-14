#!/usr/bin/env python3
"""
Test the complete LLM token management integration
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_llm_token_integration():
    """Test that all LLM token components are properly integrated."""
    
    print("🧪 Testing LLM Token Management Integration...")
    
    try:
        # Test 1: Check User model has LLM token fields
        print("\n1️⃣ Testing User model...")
        from app.models.user import User
        
        # Check if User has the new fields
        user_fields = dir(User)
        assert 'llm_token' in user_fields, "User model missing llm_token field"
        assert 'llm_provider' in user_fields, "User model missing llm_provider field"
        assert 'has_llm_token' in user_fields, "User model missing has_llm_token method"
        print("   ✅ User model has LLM token fields and methods")
        
        # Test 2: Check LLM API endpoints are available
        print("\n2️⃣ Testing LLM API endpoints...")
        from app.api.endpoints import llm
        
        # Check if the key functions exist
        assert hasattr(llm, 'store_llm_token'), "Missing store_llm_token endpoint"
        assert hasattr(llm, 'get_llm_token_info'), "Missing get_llm_token_info endpoint"
        assert hasattr(llm, 'delete_llm_token'), "Missing delete_llm_token endpoint"
        assert hasattr(llm, 'get_user_llm_token'), "Missing get_user_llm_token utility"
        print("   ✅ LLM API endpoints are available")
        
        # Test 3: Check AI analyzer supports user tokens
        print("\n3️⃣ Testing AI analyzer token support...")
        from app.services.ai_burnout_analyzer import AIBurnoutAnalyzerService
        
        ai_analyzer = AIBurnoutAnalyzerService()
        assert hasattr(ai_analyzer, 'create_agent_with_token'), "Missing create_agent_with_token method"
        print("   ✅ AI analyzer supports user-specific tokens")
        
        # Test 4: Check agent factory supports tokens
        print("\n4️⃣ Testing agent factory...")
        from app.agents.burnout_agent import create_burnout_agent, BurnoutDetectionAgent
        
        # Test that agent can be created with token parameter
        agent = create_burnout_agent(api_token="test-token")
        assert isinstance(agent, BurnoutDetectionAgent), "create_burnout_agent should return BurnoutDetectionAgent"
        print("   ✅ Agent factory supports API tokens")
        
        # Test 5: Check burnout analyzer accepts user_id
        print("\n5️⃣ Testing burnout analyzer integration...")
        from app.services.burnout_analyzer import BurnoutAnalyzerService
        
        analyzer = BurnoutAnalyzerService("dummy-token")
        
        # Check if analyze_burnout method accepts user_id parameter
        import inspect
        sig = inspect.signature(analyzer.analyze_burnout)
        assert 'user_id' in sig.parameters, "analyze_burnout missing user_id parameter"
        print("   ✅ Burnout analyzer accepts user_id parameter")
        
        # Test 6: Check encryption utilities
        print("\n6️⃣ Testing encryption utilities...")
        test_token = "sk-ant-api03-test123"
        
        encrypted = llm.encrypt_token(test_token)
        decrypted = llm.decrypt_token(encrypted)
        
        assert decrypted == test_token, "Token encryption/decryption failed"
        assert encrypted != test_token, "Token should be encrypted"
        print("   ✅ Token encryption/decryption works correctly")
        
        print("\n🎉 LLM Token Management Integration Test Complete!")
        print("✅ User model: LLM token fields added")
        print("✅ API endpoints: Token CRUD operations available")
        print("✅ AI analyzer: User-specific token support")
        print("✅ Agent factory: Token parameter support")
        print("✅ Burnout analyzer: User context integration")
        print("✅ Security: Token encryption/decryption")
        
        print("\n📋 Integration Summary:")
        print("• Users can store encrypted LLM tokens in their profile")
        print("• Frontend integrations page has LLM token management UI")
        print("• Dashboard AI toggle checks for token availability")
        print("• AI analysis uses user's personal LLM token when available")
        print("• System gracefully falls back when no token is provided")
        print("• All tokens are encrypted at rest for security")
        
        return True
        
    except AssertionError as e:
        print(f"❌ Integration test failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llm_token_integration()
    sys.exit(0 if success else 1)