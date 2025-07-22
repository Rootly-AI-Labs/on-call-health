"""
Sentiment Analysis Tool for Burnout Detection Agent
"""
from typing import Dict, List, Any
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import statistics


class SentimentAnalyzerTool:
    """Tool for analyzing sentiment patterns in communication data."""
    
    def __init__(self):
        self.analyzer = SentimentIntensityAnalyzer()
        self.name = "sentiment_analyzer"
        self.description = "Analyzes sentiment patterns in messages to detect communication stress indicators"
    
    def __call__(self, messages: List[str], context: str = "general") -> Dict[str, Any]:
        """
        Analyze sentiment patterns in a list of messages.
        
        Args:
            messages: List of message texts to analyze
            context: Context for analysis (e.g., 'slack', 'incident_comments', 'pr_comments')
            
        Returns:
            Dictionary with sentiment analysis results
        """
        if not messages:
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "stress_indicators": [],
                "pattern_analysis": "No messages to analyze"
            }
        
        # Analyze each message
        scores = []
        negative_messages = []
        stress_keywords = [
            "stressed", "overwhelmed", "urgent", "critical", "emergency",
            "frustrated", "tired", "exhausted", "deadline", "pressure",
            "worried", "concerned", "anxious", "burnt out", "burnout"
        ]
        
        for message in messages:
            if isinstance(message, str) and message.strip():
                score = self.analyzer.polarity_scores(message.lower())
                scores.append(score)
                
                # Check for stress indicators
                if score['compound'] <= -0.3:  # Notably negative
                    negative_messages.append(message[:100])  # First 100 chars
                    
        if not scores:
            return {
                "overall_sentiment": "neutral",
                "sentiment_score": 0.0,
                "stress_indicators": [],
                "pattern_analysis": "No valid messages to analyze"
            }
        
        # Calculate overall metrics
        compound_scores = [s['compound'] for s in scores]
        avg_compound = statistics.mean(compound_scores)
        
        # Determine overall sentiment
        if avg_compound >= 0.05:
            overall_sentiment = "positive"
        elif avg_compound <= -0.05:
            overall_sentiment = "negative"
        else:
            overall_sentiment = "neutral"
        
        # Identify stress indicators
        stress_indicators = []
        
        # High negativity rate
        negative_count = len([s for s in compound_scores if s <= -0.1])
        negativity_rate = negative_count / len(compound_scores)
        if negativity_rate > 0.3:
            stress_indicators.append(f"High negativity rate: {negativity_rate:.1%} of messages")
        
        # Sentiment volatility
        if len(compound_scores) > 3:
            sentiment_std = statistics.stdev(compound_scores)
            if sentiment_std > 0.4:
                stress_indicators.append(f"High sentiment volatility: {sentiment_std:.2f}")
        
        # Context-specific analysis
        pattern_analysis = self._analyze_patterns(scores, context, messages)
        
        # Log detailed sentiment analysis results
        logger.info(f"Sentiment Analysis Complete - Messages: {len(messages)}, Overall: {overall_sentiment}, Score: {round(avg_compound, 3)}, Negative rate: {round(negativity_rate, 3)}, Stress indicators: {len(stress_indicators)}")
        
        return {
            "overall_sentiment": overall_sentiment,
            "sentiment_score": round(avg_compound, 3),
            "total_messages": len(messages),
            "negative_rate": round(negativity_rate, 3),
            "stress_indicators": stress_indicators,
            "pattern_analysis": pattern_analysis,
            "sample_negative_messages": negative_messages[:3]  # Show first 3 negative examples
        }
    
    def _analyze_patterns(self, scores: List[Dict], context: str, messages: List[str]) -> str:
        """Analyze sentiment patterns based on context."""
        if not scores:
            return "No sentiment patterns detected"
        
        compound_scores = [s['compound'] for s in scores]
        avg_compound = statistics.mean(compound_scores)
        
        analysis = []
        
        if context == "slack":
            if avg_compound < -0.1:
                analysis.append("Communication shows signs of stress or frustration")
            elif avg_compound > 0.1:
                analysis.append("Generally positive communication tone")
            else:
                analysis.append("Neutral communication tone")
                
        elif context == "incident_comments":
            if avg_compound < -0.2:
                analysis.append("High stress levels during incident response")
            elif len([s for s in compound_scores if s < -0.3]) > len(scores) * 0.2:
                analysis.append("Frequent negative sentiment during incidents")
            else:
                analysis.append("Manageable stress levels during incident response")
                
        elif context == "pr_comments":
            negative_rate = len([s for s in compound_scores if s <= -0.1]) / len(scores)
            if negative_rate > 0.4:
                analysis.append("High conflict or frustration in code reviews")
            else:
                analysis.append("Collaborative code review environment")
        
        # Check for burnout keywords
        burnout_keywords = ["burnt out", "burnout", "exhausted", "overwhelmed", "can't handle"]
        text_content = " ".join(messages).lower()
        burnout_mentions = [kw for kw in burnout_keywords if kw in text_content]
        if burnout_mentions:
            analysis.append(f"Direct burnout indicators mentioned: {', '.join(burnout_mentions)}")
        
        return "; ".join(analysis) if analysis else "No specific patterns detected"


def create_sentiment_analyzer_tool():
    """Factory function to create sentiment analyzer tool for smolagents."""
    tool = SentimentAnalyzerTool()
    
    def sentiment_analyzer(messages: List[str], context: str = "general") -> Dict[str, Any]:
        """
        Analyze sentiment patterns in messages to detect communication stress.
        
        Args:
            messages: List of message texts to analyze
            context: Context for analysis ('slack', 'incident_comments', 'pr_comments')
            
        Returns:
            Dictionary with sentiment analysis including overall sentiment, stress indicators, and patterns
        """
        return tool(messages, context)
    
    return sentiment_analyzer