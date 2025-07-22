"""
Pattern Analysis Tool for Burnout Detection Agent
"""
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import statistics
from collections import defaultdict, Counter


class PatternAnalyzerTool:
    """Tool for analyzing work patterns and detecting burnout indicators."""
    
    def __init__(self):
        self.name = "pattern_analyzer"
        self.description = "Analyzes work patterns across different data sources to identify burnout risk factors"
    
    def __call__(self, data_type: str, events: List[Dict[str, Any]], analysis_window_days: int = 30) -> Dict[str, Any]:
        """
        Analyze patterns in work-related events.
        
        Args:
            data_type: Type of data ('incidents', 'commits', 'messages', 'prs')
            events: List of events with timestamp and metadata
            analysis_window_days: Days to analyze (default 30)
            
        Returns:
            Dictionary with pattern analysis results
        """
        if not events:
            return {
                "pattern_type": data_type,
                "total_events": 0,
                "burnout_indicators": [],
                "pattern_summary": "No events to analyze",
                "recommendations": []
            }
        
        # Parse and validate events
        parsed_events = self._parse_events(events)
        if not parsed_events:
            return {
                "pattern_type": data_type,
                "total_events": len(events),
                "burnout_indicators": [],
                "pattern_summary": "No valid timestamp data found",
                "recommendations": []
            }
        
        # Analyze patterns based on data type
        if data_type == "incidents":
            return self._analyze_incident_patterns(parsed_events, analysis_window_days)
        elif data_type == "commits":
            return self._analyze_commit_patterns(parsed_events, analysis_window_days)
        elif data_type == "messages":
            return self._analyze_message_patterns(parsed_events, analysis_window_days)
        elif data_type == "prs":
            return self._analyze_pr_patterns(parsed_events, analysis_window_days)
        else:
            return self._analyze_generic_patterns(parsed_events, analysis_window_days, data_type)
    
    def _parse_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse and validate event timestamps."""
        parsed = []
        for event in events:
            if not isinstance(event, dict):
                continue
                
            # Try to find timestamp in various fields
            timestamp = None
            for field in ['timestamp', 'created_at', 'date', 'time', 'occurred_at']:
                if field in event:
                    timestamp = event[field]
                    break
            
            if timestamp:
                try:
                    if isinstance(timestamp, str):
                        # Try parsing common ISO formats
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    elif isinstance(timestamp, (int, float)):
                        dt = datetime.fromtimestamp(timestamp)
                    else:
                        continue
                    
                    parsed.append({
                        **event,
                        'parsed_datetime': dt,
                        'hour': dt.hour,
                        'weekday': dt.weekday(),  # 0=Monday, 6=Sunday
                        'is_weekend': dt.weekday() >= 5
                    })
                except (ValueError, TypeError):
                    continue
        
        return parsed
    
    def _analyze_incident_patterns(self, events: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
        """Analyze incident response patterns."""
        burnout_indicators = []
        
        # Time distribution analysis
        hour_counts = Counter(event['hour'] for event in events)
        weekend_count = sum(1 for event in events if event['is_weekend'])
        
        # After-hours work (6 PM to 8 AM)
        after_hours_count = sum(1 for event in events if event['hour'] >= 18 or event['hour'] <= 8)
        after_hours_rate = after_hours_count / len(events) if events else 0
        
        if after_hours_rate > 0.3:
            burnout_indicators.append(f"High after-hours incident response: {after_hours_rate:.1%}")
        
        # Weekend work
        weekend_rate = weekend_count / len(events) if events else 0
        if weekend_rate > 0.2:
            burnout_indicators.append(f"Frequent weekend incident response: {weekend_rate:.1%}")
        
        # Incident frequency analysis
        daily_counts = defaultdict(int)
        for event in events:
            date_key = event['parsed_datetime'].date()
            daily_counts[date_key] += 1
        
        daily_incident_counts = list(daily_counts.values())
        if daily_incident_counts:
            avg_daily = statistics.mean(daily_incident_counts)
            max_daily = max(daily_incident_counts)
            
            if max_daily > avg_daily * 3:
                burnout_indicators.append(f"High incident load spikes: max {max_daily} vs avg {avg_daily:.1f}")
        
        # Response time analysis (if available)
        response_times = []
        for event in events:
            if 'response_time_minutes' in event:
                response_times.append(event['response_time_minutes'])
        
        response_pressure = ""
        if response_times:
            avg_response = statistics.mean(response_times)
            if avg_response < 5:  # Very fast response expected
                response_pressure = "High response time pressure detected"
                burnout_indicators.append(response_pressure)
        
        pattern_summary = f"Analyzed {len(events)} incidents over {window_days} days. "
        pattern_summary += f"After-hours: {after_hours_rate:.1%}, Weekend: {weekend_rate:.1%}"
        
        recommendations = self._generate_incident_recommendations(burnout_indicators, after_hours_rate, weekend_rate)
        
        return {
            "pattern_type": "incidents",
            "total_events": len(events),
            "after_hours_rate": round(after_hours_rate, 3),
            "weekend_rate": round(weekend_rate, 3),
            "peak_hours": [h for h, count in hour_counts.most_common(3)],
            "burnout_indicators": burnout_indicators,
            "pattern_summary": pattern_summary,
            "recommendations": recommendations
        }
    
    def _analyze_commit_patterns(self, events: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
        """Analyze code commit patterns."""
        burnout_indicators = []
        
        # Time distribution
        hour_counts = Counter(event['hour'] for event in events)
        weekend_count = sum(1 for event in events if event['is_weekend'])
        
        # Late night coding (10 PM to 6 AM)
        late_night_count = sum(1 for event in events if event['hour'] >= 22 or event['hour'] <= 6)
        late_night_rate = late_night_count / len(events) if events else 0
        
        if late_night_rate > 0.2:
            burnout_indicators.append(f"Excessive late-night coding: {late_night_rate:.1%}")
        
        # Weekend coding
        weekend_rate = weekend_count / len(events) if events else 0
        if weekend_rate > 0.15:
            burnout_indicators.append(f"High weekend coding activity: {weekend_rate:.1%}")
        
        # Commit frequency analysis
        daily_commits = defaultdict(int)
        for event in events:
            date_key = event['parsed_datetime'].date()
            daily_commits[date_key] += 1
        
        daily_counts = list(daily_commits.values())
        if daily_counts:
            avg_daily = statistics.mean(daily_counts)
            if avg_daily > 15:  # Very high commit frequency
                burnout_indicators.append(f"Excessive commit frequency: {avg_daily:.1f} per day")
        
        # Commit size analysis (if available)
        large_commits = 0
        for event in events:
            if 'changes' in event and event['changes'] > 500:  # Large changes
                large_commits += 1
        
        if large_commits > len(events) * 0.3:
            burnout_indicators.append("High frequency of large commits (potential code dumps)")
        
        pattern_summary = f"Analyzed {len(events)} commits over {window_days} days. "
        pattern_summary += f"Late-night: {late_night_rate:.1%}, Weekend: {weekend_rate:.1%}"
        
        recommendations = self._generate_commit_recommendations(burnout_indicators, late_night_rate, weekend_rate)
        
        # Log detailed pattern analysis results
        logger.info(f"Pattern Analysis (Commits) Complete - Events: {len(events)}, Late-night rate: {late_night_rate:.2%}, Weekend rate: {weekend_rate:.2%}, Burnout indicators: {len(burnout_indicators)}")
        
        return {
            "pattern_type": "commits",
            "total_events": len(events),
            "late_night_rate": round(late_night_rate, 3),
            "weekend_rate": round(weekend_rate, 3),
            "avg_daily_commits": round(statistics.mean(daily_counts), 2) if daily_counts else 0,
            "peak_hours": [h for h, count in hour_counts.most_common(3)],
            "burnout_indicators": burnout_indicators,
            "pattern_summary": pattern_summary,
            "recommendations": recommendations
        }
    
    def _analyze_message_patterns(self, events: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
        """Analyze communication message patterns."""
        burnout_indicators = []
        
        # Time distribution
        hour_counts = Counter(event['hour'] for event in events)
        weekend_count = sum(1 for event in events if event['is_weekend'])
        
        # After-hours messaging
        after_hours_count = sum(1 for event in events if event['hour'] >= 18 or event['hour'] <= 8)
        after_hours_rate = after_hours_count / len(events) if events else 0
        
        if after_hours_rate > 0.25:
            burnout_indicators.append(f"High after-hours communication: {after_hours_rate:.1%}")
        
        # Weekend messaging
        weekend_rate = weekend_count / len(events) if events else 0
        if weekend_rate > 0.15:
            burnout_indicators.append(f"Frequent weekend communication: {weekend_rate:.1%}")
        
        # Message frequency analysis
        daily_messages = defaultdict(int)
        for event in events:
            date_key = event['parsed_datetime'].date()
            daily_messages[date_key] += 1
        
        daily_counts = list(daily_messages.values())
        if daily_counts:
            avg_daily = statistics.mean(daily_counts)
            if avg_daily > 50:  # Very high message frequency
                burnout_indicators.append(f"Excessive messaging frequency: {avg_daily:.1f} per day")
        
        pattern_summary = f"Analyzed {len(events)} messages over {window_days} days. "
        pattern_summary += f"After-hours: {after_hours_rate:.1%}, Weekend: {weekend_rate:.1%}"
        
        recommendations = self._generate_message_recommendations(burnout_indicators, after_hours_rate, weekend_rate)
        
        return {
            "pattern_type": "messages",
            "total_events": len(events),
            "after_hours_rate": round(after_hours_rate, 3),
            "weekend_rate": round(weekend_rate, 3),
            "avg_daily_messages": round(statistics.mean(daily_counts), 2) if daily_counts else 0,
            "peak_hours": [h for h, count in hour_counts.most_common(3)],
            "burnout_indicators": burnout_indicators,
            "pattern_summary": pattern_summary,
            "recommendations": recommendations
        }
    
    def _analyze_pr_patterns(self, events: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
        """Analyze pull request patterns."""
        burnout_indicators = []
        
        # Time analysis
        weekend_count = sum(1 for event in events if event['is_weekend'])
        weekend_rate = weekend_count / len(events) if events else 0
        
        if weekend_rate > 0.2:
            burnout_indicators.append(f"High weekend PR activity: {weekend_rate:.1%}")
        
        # PR size analysis (if available)
        large_prs = 0
        for event in events:
            if 'size' in event and event['size'] > 1000:  # Large PRs
                large_prs += 1
        
        if large_prs > len(events) * 0.4:
            burnout_indicators.append("High frequency of large PRs (potential lack of incremental development)")
        
        pattern_summary = f"Analyzed {len(events)} PRs over {window_days} days. Weekend: {weekend_rate:.1%}"
        
        return {
            "pattern_type": "prs",
            "total_events": len(events),
            "weekend_rate": round(weekend_rate, 3),
            "large_pr_rate": round(large_prs / len(events), 3) if events else 0,
            "burnout_indicators": burnout_indicators,
            "pattern_summary": pattern_summary,
            "recommendations": []
        }
    
    def _analyze_generic_patterns(self, events: List[Dict[str, Any]], window_days: int, data_type: str) -> Dict[str, Any]:
        """Generic pattern analysis for unknown data types."""
        weekend_count = sum(1 for event in events if event['is_weekend'])
        weekend_rate = weekend_count / len(events) if events else 0
        
        hour_counts = Counter(event['hour'] for event in events)
        
        return {
            "pattern_type": data_type,
            "total_events": len(events),
            "weekend_rate": round(weekend_rate, 3),
            "peak_hours": [h for h, count in hour_counts.most_common(3)],
            "burnout_indicators": [],
            "pattern_summary": f"Analyzed {len(events)} {data_type} events over {window_days} days",
            "recommendations": []
        }
    
    def _generate_incident_recommendations(self, indicators: List[str], after_hours_rate: float, weekend_rate: float) -> List[str]:
        """Generate recommendations based on incident patterns."""
        recommendations = []
        
        if after_hours_rate > 0.3:
            recommendations.append("Consider implementing better on-call rotation to reduce individual after-hours load")
        
        if weekend_rate > 0.2:
            recommendations.append("Review weekend incident patterns - consider preventive measures or better coverage")
        
        if len(indicators) > 2:
            recommendations.append("Multiple burnout indicators detected - recommend immediate workload review")
        
        return recommendations
    
    def _generate_commit_recommendations(self, indicators: List[str], late_night_rate: float, weekend_rate: float) -> List[str]:
        """Generate recommendations based on commit patterns."""
        recommendations = []
        
        if late_night_rate > 0.2:
            recommendations.append("High late-night coding detected - encourage better work-life boundaries")
        
        if weekend_rate > 0.15:
            recommendations.append("Frequent weekend coding - consider workload distribution improvements")
        
        return recommendations
    
    def _generate_message_recommendations(self, indicators: List[str], after_hours_rate: float, weekend_rate: float) -> List[str]:
        """Generate recommendations based on message patterns."""
        recommendations = []
        
        if after_hours_rate > 0.25:
            recommendations.append("High after-hours communication - establish communication boundaries")
        
        if weekend_rate > 0.15:
            recommendations.append("Frequent weekend messaging - encourage disconnection during rest periods")
        
        return recommendations


def create_pattern_analyzer_tool():
    """Factory function to create pattern analyzer tool for smolagents."""
    tool = PatternAnalyzerTool()
    
    def pattern_analyzer(data_type: str, events: List[Dict[str, Any]], analysis_window_days: int = 30) -> Dict[str, Any]:
        """
        Analyze patterns in work-related events to detect burnout indicators.
        
        Args:
            data_type: Type of data ('incidents', 'commits', 'messages', 'prs')
            events: List of events with timestamp and metadata
            analysis_window_days: Days to analyze (default 30)
            
        Returns:
            Dictionary with pattern analysis including burnout indicators and recommendations
        """
        return tool(data_type, events, analysis_window_days)
    
    return pattern_analyzer