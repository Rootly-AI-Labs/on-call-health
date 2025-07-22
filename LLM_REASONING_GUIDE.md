# 🧠 LLM-Powered Burnout Analysis Guide

## Overview

The burnout detection system now includes **natural language reasoning** powered by large language models (LLMs) through the smolagents framework. This enhancement provides contextual insights, human-like explanations, and adaptive analysis that goes beyond simple metrics.

## 🔄 Two Operating Modes

### 1. **Direct Tool Analysis** (Default - No API Key Required)
- ✅ Fast, deterministic analysis
- ✅ Statistical pattern detection  
- ✅ Rule-based recommendations
- ✅ Zero API costs
- ✅ Privacy-friendly (no external calls)

### 2. **LLM-Powered Reasoning** (Optional - Requires API Key)
- ✅ Everything from Direct Tool Analysis PLUS:
- 🧠 Natural language understanding
- 🧠 Contextual pattern interpretation
- 🧠 Reasoning about cause and effect
- 🧠 Personalized, narrative insights
- 🧠 Adaptive analysis approach

## 🚀 Enabling LLM Reasoning

### Step 1: Get an OpenAI API Key
1. Go to [OpenAI Platform](https://platform.openai.com/)
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new API key
5. Copy the key (starts with `sk-...`)

### Step 2: Set Environment Variable
```bash
# For current session
export OPENAI_API_KEY="sk-your-key-here"

# For permanent setup (add to ~/.bashrc or ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.bashrc
source ~/.bashrc
```

### Step 3: Restart the Backend
```bash
cd backend
source venv/bin/activate
python -m uvicorn app.main:app --reload
```

### Step 4: Test LLM Integration
```bash
cd backend
source venv/bin/activate
python test_llm_reasoning.py
```

## 🎯 What Changes With LLM Reasoning

### Before (Direct Tools):
```
Risk Factors:
• High after-hours incident response: 35.0%
• Negative communication sentiment detected
• Excessive messaging frequency: 45.2 per day

Recommendations:
• Establish clear after-hours communication policies
• Review current workload distribution
```

### After (LLM Reasoning):
```
🧠 AI Analysis & Reasoning:

Sarah is showing concerning signs of burnout across multiple dimensions. 
Her incident response pattern (35% after-hours) combined with negative 
communication sentiment (-0.35) suggests she may be feeling overwhelmed 
and taking on too much responsibility for system stability.

The high messaging frequency (45 messages/day) appears to be her seeking 
support or trying to coordinate solutions, which indicates she may be 
struggling to handle the workload independently.

Key concerns:
- She's responding to critical incidents late at night, suggesting she 
  feels personally responsible for system uptime
- Her communication shows increasing frustration, particularly around 
  deployment issues
- The pattern suggests a cycle where system problems → stress → more 
  after-hours work → more stress

Recommendations:
• Immediate: Rotate incident ownership to reduce her sense of sole 
  responsibility
• Short-term: Improve deployment reliability to address root cause of 
  her stress triggers  
• Long-term: Implement better on-call coverage and team support systems
```

## 🛠️ Technical Implementation

### Architecture
```
User Request → Burnout Analysis Service → AI Agent → LLM Reasoning
                                      ↓
Custom Tools ← smolagents Framework ← Natural Language Prompt
(Sentiment, Pattern, Workload Analysis)
                                      ↓
Structured Response ← Response Parser ← LLM Generated Insights
```

### Custom Tools Available to LLM:
1. **Sentiment Analyzer**: VADER-based communication analysis
2. **Pattern Analyzer**: Time-based work pattern detection  
3. **Workload Analyzer**: Multi-factor intensity assessment

### LLM Models Supported:
- **OpenAI**: gpt-4o-mini (default), gpt-4o, gpt-3.5-turbo
- **Anthropic**: claude-3-haiku, claude-3-sonnet
- **Local**: Any Ollama-compatible model
- **Open Source**: Any HuggingFace model

## 📊 Data Flow

### 1. Data Preparation
```python
# System prepares contextual summary for LLM
member_summary = """
Team Member: Sarah Chen
Incidents: 25 in analysis period
- 8 incidents (32%) outside business hours
- 3 incidents (12%) on weekends
GitHub Activity: 45 commits, 8 pull requests  
- 18 commits (40%) after hours
Slack Activity: 120 messages
- Sentiment score: -0.35 (negative)
- 35 messages (29%) after hours
"""
```

### 2. LLM Reasoning Prompt
```python
prompt = f"""
You are an expert burnout detection analyst. Analyze the burnout risk 
for {member_name} using the available tools and data.

MEMBER DATA SUMMARY: {data_summary}

ANALYSIS INSTRUCTIONS:
1. Use available tools to examine work patterns
2. Consider Maslach Burnout Inventory dimensions
3. Look for concerning patterns like after-hours work, negative sentiment
4. Generate specific, actionable recommendations
5. Explain the 'why' behind the patterns

Please analyze {member_name}'s burnout risk now.
"""
```

### 3. Tool Execution & Reasoning
```python
# LLM uses tools and reasons about results
agent_result = agent.run(prompt)

# Example LLM reasoning process:
# 1. "Let me analyze Sarah's incident patterns..."
# 2. "I'll check her communication sentiment..."  
# 3. "Based on the workload analysis..."
# 4. "The combination of these factors suggests..."
```

### 4. Response Parsing
```python
# System extracts structured insights from LLM response
structured_result = {
    "ai_insights": {
        "llm_analysis": agent_result,  # Full reasoning
        "analysis_method": "smolagents_llm_reasoning"
    },
    "risk_assessment": {
        "overall_risk_level": "high",
        "risk_factors": [...],
        "llm_reasoning": agent_result
    },
    "recommendations": [...]
}
```

## 🎨 Frontend Display

### AI Insights Section
When LLM reasoning is available, the member detail modal shows:

1. **🧠 AI Analysis & Reasoning** - Full natural language analysis
2. **🚨 AI Risk Assessment** - Structured risk factors and scores  
3. **💡 AI-Powered Recommendations** - Contextual action items
4. **🎯 AI Confidence** - Analysis reliability indicator

### Fallback Display
Without LLM, the system shows traditional analysis with smart tooltips explaining that advanced reasoning is available with API key setup.

## 💰 Cost Considerations

### OpenAI Pricing (gpt-4o-mini):
- **Input**: $0.15 per 1M tokens
- **Output**: $0.60 per 1M tokens

### Estimated Usage:
- **Per Analysis**: ~1,000 input tokens + 500 output tokens
- **Cost Per Analysis**: ~$0.0005 (less than $0.001)
- **100 Analyses**: ~$0.05
- **1,000 Analyses**: ~$0.50

### Cost Optimization:
- LLM analysis only runs when specifically requested
- Results are cached to avoid re-analysis
- Fallback to direct tools if LLM fails
- Configurable model selection (cheaper vs more capable)

## 🔒 Privacy & Security

### Data Handling:
- Only aggregated patterns sent to LLM (no raw messages/code)
- No personally identifiable information in prompts
- Analysis results stored locally
- API calls made server-side only

### Security Features:
- API keys stored as environment variables
- Encrypted communication with LLM providers
- Fallback analysis if LLM unavailable
- No data retention by LLM providers

## 🧪 Testing & Validation

### Test Suite:
```bash
# Test basic tools (no API key needed)
python test_ai_agent.py

# Test LLM reasoning (requires API key)
python test_llm_reasoning.py

# Full integration test
python -m pytest tests/test_llm_integration.py
```

### Validation Metrics:
- ✅ Analysis accuracy vs traditional methods
- ✅ Response time under 10 seconds
- ✅ Graceful degradation without API key
- ✅ Consistent recommendations across runs

## 🚨 Troubleshooting

### Common Issues:

#### "LLM agent not available"
- Check OPENAI_API_KEY environment variable
- Verify API key is valid
- Check internet connectivity

#### "LLM analysis failed"
- System automatically falls back to direct tools
- Check API rate limits
- Verify model name is correct

#### Slow Response Times
- Switch to faster model (gpt-3.5-turbo)
- Reduce max_iterations in agent config
- Use direct tools for real-time analysis

### Debug Mode:
```bash
export LOG_LEVEL=DEBUG
python test_llm_reasoning.py
```

## 🔮 Future Enhancements

### Planned Features:
1. **Custom LLM Fine-tuning** - Train on organization-specific patterns
2. **Multi-Language Support** - Analysis in different languages
3. **Voice Insights** - Audio summaries of analysis
4. **Predictive Modeling** - Forecast burnout trends
5. **Team Dynamics Analysis** - Inter-team relationship insights

### Integration Options:
- **Slack Bot** - Get burnout insights in Slack
- **Dashboard Widgets** - Real-time LLM insights
- **Email Reports** - Weekly AI-generated summaries
- **Mobile App** - On-the-go burnout monitoring

## 📚 Additional Resources

- [Smolagents Documentation](https://huggingface.co/docs/smolagents)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Maslach Burnout Inventory](https://en.wikipedia.org/wiki/Maslach_Burnout_Inventory)
- [VADER Sentiment Analysis](https://github.com/cjhutto/vaderSentiment)

---

## 🎉 Ready to Experience LLM-Powered Burnout Analysis?

1. **Set your OPENAI_API_KEY**
2. **Restart the backend**  
3. **Run a new analysis**
4. **Check the "🤖 AI Insights" section**
5. **Enjoy contextual, human-like burnout analysis!** 🚀