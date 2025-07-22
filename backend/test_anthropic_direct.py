#!/usr/bin/env python3
"""
Direct test of Anthropic API integration
"""
import os

def test_anthropic_direct():
    """Test direct Anthropic API call."""
    api_key = "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"
    
    try:
        from anthropic import Anthropic
        
        print("🧪 Testing direct Anthropic API...")
        client = Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=100,
            messages=[
                {"role": "user", "content": "Analyze this burnout scenario: A developer is working 40% after-hours and shows negative communication sentiment. Provide a brief insight."}
            ]
        )
        
        print("✅ Direct Anthropic API working!")
        print(f"Response: {response.content[0].text}")
        return True
        
    except Exception as e:
        print(f"❌ Direct Anthropic test failed: {e}")
        return False

def test_litellm_anthropic():
    """Test LiteLLM with Anthropic."""
    os.environ['ANTHROPIC_API_KEY'] = "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"
    
    try:
        import litellm
        
        print("\n🧪 Testing LiteLLM with Anthropic...")
        
        response = litellm.completion(
            model="claude-3-haiku-20240307",
            messages=[
                {"role": "user", "content": "Give me a brief burnout analysis insight in one sentence."}
            ],
            max_tokens=50
        )
        
        print("✅ LiteLLM + Anthropic working!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print(f"❌ LiteLLM + Anthropic test failed: {e}")
        return False

def test_smolagents_anthropic():
    """Test smolagents with Anthropic."""
    os.environ['ANTHROPIC_API_KEY'] = "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"
    
    try:
        from smolagents import CodeAgent, LiteLLMModel
        
        print("\n🧪 Testing smolagents with Anthropic...")
        
        # Simple test without custom tools
        agent = CodeAgent(
            tools=[],
            model=LiteLLMModel("claude-3-haiku-20240307"),
        )
        
        result = agent.run("Explain burnout in software engineering in one sentence.")
        
        print("✅ Smolagents + Anthropic working!")
        print(f"Response: {result}")
        return True
        
    except Exception as e:
        print(f"❌ Smolagents + Anthropic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🔬 Testing Anthropic Integration")
    print("=" * 50)
    
    success1 = test_anthropic_direct()
    success2 = test_litellm_anthropic()
    success3 = test_smolagents_anthropic()
    
    if success1 and success2 and success3:
        print("\n🎉 All Anthropic integration tests passed!")
        print("Ready to use Claude for burnout analysis! 🚀")
    else:
        print("\n❌ Some tests failed. Let's debug...")