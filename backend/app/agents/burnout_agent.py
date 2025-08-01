"""
Burnout Detection Agent using smolagents framework
"""
from typing import Dict, List, Any, Optional
import json
import logging
from datetime import datetime

try:
    from smolagents import CodeAgent, HfApiModel
except ImportError:
    # Fallback for development/testing
    CodeAgent = None
    HfApiModel = None

from .tools.sentiment_analyzer import create_sentiment_analyzer_tool
from .tools.pattern_analyzer import create_pattern_analyzer_tool
from .tools.workload_analyzer import create_workload_analyzer_tool

logger = logging.getLogger(__name__)


class BurnoutDetectionAgent:
    """
    AI Agent for dynamic burnout detection and analysis.
    
    Uses smolagents framework with custom tools to provide intelligent,
    adaptive analysis of burnout risk factors across multiple data sources.
    """
    
    def __init__(self, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize the burnout detection agent.
        
        Args:
            model_name: Name of the language model to use
            api_key: Optional API key for LLM access
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize custom tools
        self.sentiment_analyzer = create_sentiment_analyzer_tool()
        self.pattern_analyzer = create_pattern_analyzer_tool()
        self.workload_analyzer = create_workload_analyzer_tool()
        
        # Initialize agent if smolagents is available
        self.agent = None
        self.agent_available = False
        
        if CodeAgent and api_key:
            try:
                # Try to initialize with LLM (requires API key)
                from smolagents import LiteLLMModel
                
                self.tools = [
                    self.sentiment_analyzer,
                    self.pattern_analyzer, 
                    self.workload_analyzer
                ]
                
                # Create the actual smolagents agent with reasoning capabilities
                # Configure the model with the API key
                import os
                os.environ["ANTHROPIC_API_KEY"] = api_key  # Set for LiteLLM
                
                self.agent = CodeAgent(
                    tools=self.tools,
                    model=LiteLLMModel(model_name),
                    max_iterations=3  # Allow multiple reasoning steps
                )
                
                self.agent_available = True
                self.logger.info(f"Smolagents agent initialized with {model_name} for natural language reasoning")
                
            except Exception as e:
                self.logger.warning(f"Could not initialize smolagents with LLM: {e}")
                self.logger.info("Falling back to direct tool usage")
                self.agent_available = False
        elif CodeAgent and not api_key:
            self.logger.info("No API key provided - using direct tool analysis instead of LLM reasoning")
            self.agent_available = False
        else:
            self.logger.warning("smolagents not available - using direct tool analysis")
            self.agent_available = False
    
    def analyze_member_burnout(
        self, 
        member_data: Dict[str, Any], 
        available_data_sources: List[str],
        team_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive burnout analysis for a team member.
        
        Args:
            member_data: Individual member's data across all sources
            available_data_sources: List of available data sources ('github', 'slack', 'incidents')
            team_context: Optional team statistics for comparison
            
        Returns:
            Dictionary with AI-powered burnout analysis and recommendations
        """
        try:
            if self.agent_available:
                return self._agent_analysis(member_data, available_data_sources, team_context)
            else:
                return self._fallback_analysis(member_data, available_data_sources, team_context)
        except Exception as e:
            self.logger.error(f"Error in burnout analysis: {e}")
            return self._error_response(str(e))
    
    def _agent_analysis(
        self, 
        member_data: Dict[str, Any], 
        available_data_sources: List[str],
        team_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform analysis using the AI agent with natural language reasoning.
        """
        try:
            # Create detailed prompt for the LLM to reason about
            member_name = member_data.get("name", "Team Member")
            
            # Prepare data summary for the LLM
            data_summary = self._prepare_data_summary(member_data, available_data_sources)
            
            # Create reasoning prompt
            prompt = f"""
You are an expert burnout detection analyst. Analyze the burnout risk for {member_name} using the available tools and data.

AVAILABLE DATA SOURCES: {', '.join(available_data_sources)}

MEMBER DATA SUMMARY:
{data_summary}

ANALYSIS INSTRUCTIONS:
1. Use the available tools (sentiment_analyzer, pattern_analyzer, workload_analyzer) to examine different aspects of their work patterns
2. Consider the Maslach Burnout Inventory dimensions: Emotional Exhaustion, Depersonalization, Personal Accomplishment
3. Look for concerning patterns like after-hours work, negative sentiment, excessive workload
4. Generate specific, actionable recommendations based on the data patterns you discover
5. Provide a confidence assessment based on data quality and quantity

Focus on generating insights that go beyond simple metrics - explain the "why" behind the patterns and provide contextual understanding.

Please analyze {member_name}'s burnout risk now.
"""

            # Use smolagents to run the analysis with reasoning
            self.logger.info(f"Running LLM-powered analysis for {member_name}")
            self.logger.info(f"AI Analysis Input - Data sources: {available_data_sources}, Incident count: {len(member_data.get('incidents', []))}, Metrics: {list(member_data.keys())}")
            
            agent_result = self.agent.run(prompt)
            
            # Log the raw AI response for debugging
            self.logger.info(f"AI Agent Raw Response for {member_name}: {str(agent_result)[:500]}...")
            
            # Parse and structure the agent's natural language response
            structured_result = self._parse_agent_response(agent_result, member_data, available_data_sources)
            
            # Log the structured AI insights
            if structured_result:
                confidence = structured_result.get('confidence_score', 'unknown')
                risk_level = structured_result.get('overall_risk_level', 'unknown')
                insight_count = len(structured_result.get('insights', []))
                recommendation_count = len(structured_result.get('recommendations', []))
                self.logger.info(f"AI Analysis Output for {member_name} - Risk: {risk_level}, Confidence: {confidence}, Insights: {insight_count}, Recommendations: {recommendation_count}")
            
            return structured_result
            
        except Exception as e:
            self.logger.error(f"LLM analysis failed: {e}")
            # Fallback to direct tool analysis
            self.logger.info("Falling back to direct tool analysis")
            return self._comprehensive_analysis(member_data, available_data_sources, team_context)
    
    def _fallback_analysis(
        self, 
        member_data: Dict[str, Any], 
        available_data_sources: List[str],
        team_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform analysis using direct tool calls (fallback when smolagents unavailable).
        """
        return self._comprehensive_analysis(member_data, available_data_sources, team_context)
    
    def _comprehensive_analysis(
        self, 
        member_data: Dict[str, Any], 
        available_data_sources: List[str],
        team_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive analysis using all available tools.
        """
        analysis_results = {
            "member_name": member_data.get("name", "Unknown"),
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "data_sources_analyzed": available_data_sources,
            "ai_insights": {},
            "risk_assessment": {},
            "recommendations": [],
            "confidence_score": 0.0
        }
        
        # 1. Workload Analysis
        workload_result = self.workload_analyzer(member_data, team_context)
        analysis_results["ai_insights"]["workload"] = workload_result
        
        # 2. Pattern Analysis for each data source
        pattern_results = {}
        
        if "incidents" in available_data_sources and member_data.get("incidents"):
            incident_patterns = self.pattern_analyzer("incidents", member_data["incidents"])
            pattern_results["incidents"] = incident_patterns
        
        if "github" in available_data_sources and member_data.get("commits"):
            commit_patterns = self.pattern_analyzer("commits", member_data["commits"])
            pattern_results["github_commits"] = commit_patterns
        
        if "github" in available_data_sources and member_data.get("pull_requests"):
            pr_patterns = self.pattern_analyzer("prs", member_data["pull_requests"])
            pattern_results["github_prs"] = pr_patterns
        
        if "slack" in available_data_sources and member_data.get("messages"):
            message_patterns = self.pattern_analyzer("messages", member_data["messages"])
            pattern_results["slack_messages"] = message_patterns
        
        analysis_results["ai_insights"]["patterns"] = pattern_results
        
        # 3. Sentiment Analysis (if communication data available)
        sentiment_results = {}
        
        if "slack" in available_data_sources and member_data.get("slack_messages"):
            slack_messages = [msg.get("text", "") for msg in member_data["slack_messages"] if msg.get("text")]
            if slack_messages:
                slack_sentiment = self.sentiment_analyzer(slack_messages, "slack")
                sentiment_results["slack"] = slack_sentiment
        
        if "github" in available_data_sources and member_data.get("pr_comments"):
            pr_comments = [comment.get("text", "") for comment in member_data["pr_comments"] if comment.get("text")]
            if pr_comments:
                pr_sentiment = self.sentiment_analyzer(pr_comments, "pr_comments")
                sentiment_results["github_prs"] = pr_sentiment
        
        if "incidents" in available_data_sources and member_data.get("incident_comments"):
            incident_comments = [comment.get("text", "") for comment in member_data["incident_comments"] if comment.get("text")]
            if incident_comments:
                incident_sentiment = self.sentiment_analyzer(incident_comments, "incident_comments")
                sentiment_results["incidents"] = incident_sentiment
        
        analysis_results["ai_insights"]["sentiment"] = sentiment_results
        
        # 4. Synthesize Risk Assessment
        risk_assessment = self._synthesize_risk_assessment(
            workload_result, 
            pattern_results, 
            sentiment_results,
            available_data_sources
        )
        analysis_results["risk_assessment"] = risk_assessment
        
        # 5. Generate AI-powered Recommendations
        recommendations = self._generate_ai_recommendations(
            workload_result, 
            pattern_results, 
            sentiment_results,
            risk_assessment,
            available_data_sources
        )
        analysis_results["recommendations"] = recommendations
        
        # 6. Calculate Confidence Score
        confidence = self._calculate_confidence_score(available_data_sources, member_data)
        analysis_results["confidence_score"] = confidence
        
        return analysis_results
    
    def _synthesize_risk_assessment(
        self,
        workload_result: Dict[str, Any],
        pattern_results: Dict[str, Any],
        sentiment_results: Dict[str, Any],
        data_sources: List[str]
    ) -> Dict[str, Any]:
        """
        Synthesize overall risk assessment from all analysis results.
        """
        risk_factors = []
        protective_factors = []
        overall_risk_level = "low"
        risk_score = 0.0
        
        # Workload risk factors
        workload_status = workload_result.get("workload_status", "unknown")
        if workload_status == "critical":
            risk_factors.append("Critical workload level detected")
            risk_score += 40
        elif workload_status == "high":
            risk_factors.append("High workload level")
            risk_score += 25
        elif workload_status == "moderate":
            risk_factors.append("Moderate workload concerns")
            risk_score += 15
        elif workload_status == "sustainable":
            protective_factors.append("Sustainable workload levels")
        
        # Pattern-based risk factors
        for source, patterns in pattern_results.items():
            burnout_indicators = patterns.get("burnout_indicators", [])
            for indicator in burnout_indicators:
                risk_factors.append(f"{source.title()}: {indicator}")
                risk_score += 10
        
        # Sentiment-based risk factors
        for source, sentiment in sentiment_results.items():
            overall_sentiment = sentiment.get("overall_sentiment", "neutral")
            stress_indicators = sentiment.get("stress_indicators", [])
            
            if overall_sentiment == "negative":
                risk_factors.append(f"{source.title()}: Negative communication sentiment")
                risk_score += 15
            elif overall_sentiment == "positive":
                protective_factors.append(f"{source.title()}: Positive communication tone")
            
            for indicator in stress_indicators:
                risk_factors.append(f"{source.title()}: {indicator}")
                risk_score += 8
        
        # Determine overall risk level
        if risk_score >= 60:
            overall_risk_level = "high"
        elif risk_score >= 30:
            overall_risk_level = "medium"
        else:
            overall_risk_level = "low"
        
        return {
            "overall_risk_level": overall_risk_level,
            "risk_score": min(risk_score, 100),  # Cap at 100
            "risk_factors": risk_factors,
            "protective_factors": protective_factors,
            "data_sources_contributing": list(set([source for source in data_sources if source in pattern_results or source in sentiment_results]))
        }
    
    def _generate_ai_recommendations(
        self,
        workload_result: Dict[str, Any],
        pattern_results: Dict[str, Any],
        sentiment_results: Dict[str, Any],
        risk_assessment: Dict[str, Any],
        data_sources: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Generate intelligent, context-aware recommendations.
        """
        recommendations = []
        
        # High-priority recommendations based on risk level
        risk_level = risk_assessment.get("overall_risk_level", "low")
        
        if risk_level == "high":
            recommendations.append({
                "priority": "urgent",
                "category": "immediate_action",
                "title": "Immediate Burnout Prevention Required",
                "description": "Multiple high-risk indicators detected. Immediate workload review and intervention recommended.",
                "actions": [
                    "Schedule immediate 1:1 with manager",
                    "Review current sprint commitments",
                    "Consider redistributing critical responsibilities",
                    "Evaluate need for additional team support"
                ]
            })
        
        # Workload-specific recommendations
        workload_recommendations = workload_result.get("recommendations", [])
        for rec in workload_recommendations:
            recommendations.append({
                "priority": "high" if "URGENT" in rec else "medium",
                "category": "workload_management", 
                "title": "Workload Optimization",
                "description": rec,
                "actions": self._get_workload_actions(rec)
            })
        
        # Pattern-specific recommendations
        for source, patterns in pattern_results.items():
            pattern_recommendations = patterns.get("recommendations", [])
            for rec in pattern_recommendations:
                recommendations.append({
                    "priority": "medium",
                    "category": f"{source}_optimization",
                    "title": f"{source.title()} Pattern Improvement",
                    "description": rec,
                    "actions": self._get_pattern_actions(rec, source)
                })
        
        # Sentiment-specific recommendations
        for source, sentiment in sentiment_results.items():
            if sentiment.get("overall_sentiment") == "negative":
                recommendations.append({
                    "priority": "medium",
                    "category": "communication_health",
                    "title": f"Communication Support - {source.title()}",
                    "description": f"Negative sentiment patterns detected in {source} communication",
                    "actions": [
                        "Consider team communication training",
                        "Review team dynamics and collaboration patterns",
                        "Provide additional psychological safety support"
                    ]
                })
        
        # Data-driven insights
        if len(data_sources) > 1:
            recommendations.append({
                "priority": "low",
                "category": "insights",
                "title": "Multi-Source Analysis Available",
                "description": f"Comprehensive analysis across {len(data_sources)} data sources provides high-confidence insights",
                "actions": [
                    "Leverage integrated insights for team planning",
                    "Use patterns for proactive burnout prevention",
                    "Consider this analysis model for other team members"
                ]
            })
        
        # Remove duplicates and sort by priority
        unique_recommendations = []
        seen_descriptions = set()
        
        for rec in recommendations:
            if rec["description"] not in seen_descriptions:
                unique_recommendations.append(rec)
                seen_descriptions.add(rec["description"])
        
        # Sort by priority
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
        unique_recommendations.sort(key=lambda x: priority_order.get(x["priority"], 3))
        
        return unique_recommendations
    
    def _get_workload_actions(self, recommendation: str) -> List[str]:
        """Generate specific actions for workload recommendations."""
        if "after-hours" in recommendation.lower():
            return [
                "Set clear boundaries for after-hours work",
                "Configure notification schedules",
                "Discuss on-call rotation improvements"
            ]
        elif "weekend" in recommendation.lower():
            return [
                "Establish weekend work policies",
                "Plan better work distribution",
                "Encourage proper rest periods"
            ]
        elif "incident" in recommendation.lower():
            return [
                "Review incident prevention strategies",
                "Expand on-call team",
                "Improve monitoring and alerting"
            ]
        elif "communication" in recommendation.lower():
            return [
                "Implement async communication practices",
                "Set communication windows",
                "Use message batching techniques"
            ]
        else:
            return [
                "Review current workload distribution",
                "Identify delegation opportunities",
                "Prioritize high-impact activities"
            ]
    
    def _get_pattern_actions(self, recommendation: str, source: str) -> List[str]:
        """Generate specific actions for pattern-based recommendations."""
        actions = []
        
        if "late-night" in recommendation.lower() or "after-hours" in recommendation.lower():
            actions.extend([
                "Establish coding hour boundaries",
                "Review task planning and estimation",
                "Consider workload redistribution"
            ])
        
        if "weekend" in recommendation.lower():
            actions.extend([
                "Plan better sprint management",
                "Encourage work-life separation",
                "Review project timelines"
            ])
        
        if source == "incidents":
            actions.extend([
                "Improve incident prevention",
                "Enhance monitoring capabilities",
                "Review on-call procedures"
            ])
        elif source in ["github_commits", "github_prs"]:
            actions.extend([
                "Review development workflow",
                "Consider pair programming",
                "Improve task breakdown"
            ])
        elif source == "slack_messages":
            actions.extend([
                "Optimize communication patterns",
                "Use async methods where possible",
                "Set communication expectations"
            ])
        
        return actions if actions else ["Review and optimize current practices"]
    
    def _calculate_confidence_score(self, data_sources: List[str], member_data: Dict[str, Any]) -> float:
        """
        Calculate confidence score based on data availability and quality.
        """
        confidence = 0.0
        
        # Base confidence from data source variety
        source_weight = {
            "incidents": 0.4,   # Primary source
            "github": 0.3,     # Strong secondary
            "slack": 0.3       # Strong secondary
        }
        
        for source in data_sources:
            if source in source_weight:
                confidence += source_weight[source]
        
        # Adjust based on data quantity
        data_quantity_score = 0.0
        
        if "incidents" in data_sources:
            incident_count = len(member_data.get("incidents", []))
            data_quantity_score += min(incident_count / 10, 0.3)  # Max 0.3 for incidents
        
        if "github" in data_sources:
            commit_count = len(member_data.get("commits", []))
            pr_count = len(member_data.get("pull_requests", []))
            data_quantity_score += min((commit_count + pr_count) / 20, 0.2)  # Max 0.2 for GitHub
        
        if "slack" in data_sources:
            message_count = len(member_data.get("messages", []))
            data_quantity_score += min(message_count / 50, 0.2)  # Max 0.2 for Slack
        
        confidence += data_quantity_score
        
        # Ensure confidence is between 0 and 1
        return min(max(confidence, 0.0), 1.0)
    
    def _error_response(self, error_message: str) -> Dict[str, Any]:
        """
        Return error response with basic structure.
        """
        return {
            "error": True,
            "error_message": error_message,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "ai_insights": {},
            "risk_assessment": {
                "overall_risk_level": "unknown",
                "risk_score": 0,
                "risk_factors": ["Analysis error occurred"],
                "protective_factors": []
            },
            "recommendations": [{
                "priority": "high",
                "category": "system",
                "title": "Analysis Error",
                "description": "Could not complete AI analysis. Using fallback assessment.",
                "actions": ["Contact system administrator", "Review data sources"]
            }],
            "confidence_score": 0.0
        }
    
    def _prepare_data_summary(self, member_data: Dict[str, Any], available_data_sources: List[str]) -> str:
        """
        Prepare a concise data summary for the LLM to reason about.
        """
        summary_parts = []
        
        # Basic info
        name = member_data.get("name", "Unknown")
        summary_parts.append(f"Team Member: {name}")
        
        # Incident data
        incidents = member_data.get("incidents", [])
        if incidents:
            summary_parts.append(f"Incidents: {len(incidents)} in analysis period")
            
            # Calculate quick stats
            after_hours = 0
            weekend = 0
            for incident in incidents:
                if incident.get("after_hours"):
                    after_hours += 1
                if incident.get("weekend"):
                    weekend += 1
            
            if after_hours > 0:
                summary_parts.append(f"  - {after_hours} incidents ({after_hours/len(incidents)*100:.0f}%) outside business hours")
            if weekend > 0:
                summary_parts.append(f"  - {weekend} incidents ({weekend/len(incidents)*100:.0f}%) on weekends")
        
        # GitHub data
        github_activity = member_data.get("github_activity")
        if github_activity and "github" in available_data_sources:
            commits = github_activity.get("commits_count", 0)
            prs = github_activity.get("pull_requests_count", 0)
            after_hours_commits = github_activity.get("after_hours_commits", 0)
            
            summary_parts.append(f"GitHub Activity: {commits} commits, {prs} pull requests")
            if after_hours_commits > 0:
                summary_parts.append(f"  - {after_hours_commits} commits ({after_hours_commits/max(commits,1)*100:.0f}%) after hours")
        
        # Slack data
        slack_activity = member_data.get("slack_activity")
        if slack_activity and "slack" in available_data_sources:
            messages = slack_activity.get("messages_sent", 0)
            sentiment = slack_activity.get("sentiment_score", 0)
            after_hours_msgs = slack_activity.get("after_hours_messages", 0)
            
            summary_parts.append(f"Slack Activity: {messages} messages")
            summary_parts.append(f"  - Sentiment score: {sentiment:.2f} ({'positive' if sentiment > 0.1 else 'negative' if sentiment < -0.1 else 'neutral'})")
            if after_hours_msgs > 0:
                summary_parts.append(f"  - {after_hours_msgs} messages ({after_hours_msgs/max(messages,1)*100:.0f}%) after hours")
        
        # Additional context
        if len(available_data_sources) > 1:
            summary_parts.append(f"Multi-source analysis available: {', '.join(available_data_sources)}")
        
        return "\n".join(summary_parts)
    
    def _parse_agent_response(
        self, 
        agent_result: str, 
        member_data: Dict[str, Any], 
        available_data_sources: List[str]
    ) -> Dict[str, Any]:
        """
        Parse the agent's natural language response into structured format.
        """
        # The agent_result contains the LLM's reasoning and analysis
        # We'll extract key insights and structure them
        
        member_name = member_data.get("name", "Team Member")
        
        # Try to extract structured information from the LLM response
        # This is a simplified parser - in production you might want more sophisticated parsing
        
        # Extract risk level from response
        risk_level = "medium"  # default
        if any(word in agent_result.lower() for word in ["high risk", "critical", "urgent", "severe"]):
            risk_level = "high"
        elif any(word in agent_result.lower() for word in ["low risk", "minimal", "healthy", "good"]):
            risk_level = "low"
        
        # Extract risk factors (look for bullet points or key phrases)
        risk_factors = []
        response_lines = agent_result.split('\n')
        for line in response_lines:
            line = line.strip()
            if (line.startswith('-') or line.startswith('•') or 
                'concern' in line.lower() or 'risk' in line.lower() or
                'pattern' in line.lower() or 'indicator' in line.lower()):
                if len(line) > 10:  # Skip very short lines
                    risk_factors.append(line.lstrip('- •').strip())
        
        # Extract recommendations (look for action words)
        recommendations = []
        for line in response_lines:
            line = line.strip()
            if (line.startswith('-') or line.startswith('•') or 
                any(word in line.lower() for word in ['recommend', 'suggest', 'should', 'consider', 'implement'])):
                if len(line) > 15:  # Skip very short lines
                    recommendations.append({
                        "priority": "high" if any(word in line.lower() for word in ['urgent', 'immediate', 'critical']) else "medium",
                        "category": "llm_generated",
                        "title": "AI Recommendation",
                        "description": line.lstrip('- •').strip(),
                        "actions": []  # LLM can provide actions in description
                    })
        
        # Calculate a risk score based on the response sentiment and keywords
        risk_score = 50  # baseline
        high_risk_keywords = ['critical', 'severe', 'urgent', 'concerning', 'excessive', 'dangerous']
        low_risk_keywords = ['healthy', 'good', 'sustainable', 'positive', 'balanced']
        
        for keyword in high_risk_keywords:
            if keyword in agent_result.lower():
                risk_score += 15
        
        for keyword in low_risk_keywords:
            if keyword in agent_result.lower():
                risk_score -= 10
        
        risk_score = max(0, min(100, risk_score))  # Clamp to 0-100
        
        # Structure the response
        return {
            "member_name": member_name,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "data_sources_analyzed": available_data_sources,
            "ai_insights": {
                "llm_analysis": agent_result,  # Full LLM reasoning
                "analysis_method": "smolagents_llm_reasoning",
                "model_used": "LLM with natural language reasoning"
            },
            "risk_assessment": {
                "overall_risk_level": risk_level,
                "risk_score": risk_score,
                "risk_factors": risk_factors[:5],  # Top 5 factors
                "protective_factors": [],  # Could extract these too
                "data_sources_contributing": available_data_sources,
                "llm_reasoning": agent_result  # Include full reasoning
            },
            "recommendations": recommendations[:3],  # Top 3 recommendations
            "confidence_score": 0.8 if len(available_data_sources) > 1 else 0.6,  # Higher confidence with more data
            "analysis_type": "llm_powered_reasoning"
        }


def create_burnout_agent(model_name: str = "gpt-4o-mini", api_key: Optional[str] = None) -> BurnoutDetectionAgent:
    """
    Factory function to create a burnout detection agent.
    
    Args:
        model_name: Name of the language model to use
        api_key: Optional API key for LLM access
        
    Returns:
        Configured BurnoutDetectionAgent instance
    """
    return BurnoutDetectionAgent(model_name, api_key)