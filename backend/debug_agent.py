#!/usr/bin/env python3
"""
Debug the agent initialization
"""
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

os.environ['ANTHROPIC_API_KEY'] = "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"

def debug_agent_init():
    """Debug agent initialization step by step."""
    
    print("🔍 Debugging agent initialization...")
    
    # Test 1: Import smolagents
    try:
        from smolagents import CodeAgent, LiteLLMModel
        print("✅ Successfully imported smolagents")
    except Exception as e:
        print(f"❌ Failed to import smolagents: {e}")
        return
    
    # Test 2: Create model
    try:
        model = LiteLLMModel("claude-3-haiku-20240307")
        print("✅ Successfully created LiteLLM model")
    except Exception as e:
        print(f"❌ Failed to create model: {e}")
        return
    
    # Test 3: Import our tools
    try:
        from app.agents.tools.sentiment_analyzer import create_sentiment_analyzer_tool
        from app.agents.tools.pattern_analyzer import create_pattern_analyzer_tool
        from app.agents.tools.workload_analyzer import create_workload_analyzer_tool
        
        sentiment_tool = create_sentiment_analyzer_tool()
        pattern_tool = create_pattern_analyzer_tool()
        workload_tool = create_workload_analyzer_tool()
        
        tools = [sentiment_tool, pattern_tool, workload_tool]
        print("✅ Successfully created custom tools")
    except Exception as e:
        print(f"❌ Failed to create tools: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Create agent
    try:
        agent = CodeAgent(
            tools=tools,
            model=model
        )
        print("✅ Successfully created CodeAgent")
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 5: Simple agent run
    try:
        result = agent.run("What is burnout?")
        print("✅ Successfully ran agent")
        print(f"Result: {result}")
    except Exception as e:
        print(f"❌ Failed to run agent: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("🎉 All tests passed!")

if __name__ == "__main__":
    debug_agent_init()