"""
Cross-Platform Correlation Tool for Burnout Detection Agent

Finds correlations and patterns across different data sources:
- Incident timing vs code commits
- Communication spikes around incidents
- GitHub activity vs Slack sentiment
- Weekend work patterns across platforms
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import statistics
import logging

try:
    from smolagents import BaseTool
except ImportError:
    # Fallback for development/testing when smolagents not available
    class BaseTool:
        def __init__(self, name, description):
            self.name = name
            self.description = description

logger = logging.getLogger(__name__)


class CrossPlatformCorrelatorTool(BaseTool):
    """Tool for finding correlations across different data platforms."""
    
    def __init__(self):
        try:
            # Try the smolagents BaseTool signature
            super().__init__()
            self.name = "cross_platform_correlator"
            self.description = "Analyzes correlations between incidents, code activity, and communication patterns"
        except TypeError:
            # Fallback to our custom BaseTool signature  
            super().__init__(
                name="cross_platform_correlator",
                description="Analyzes correlations between incidents, code activity, and communication patterns"
            )
        
    def __call__(
        self, 
        incidents: List[Dict], 
        github_data: Dict[str, Any], 
        slack_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Find correlations across different data sources.
        
        Args:
            incidents: List of incident data
            github_data: GitHub activity data
            slack_data: Slack communication data
            
        Returns:
            Dictionary with correlation analysis and insights
        """
        correlations = {
            "incident_code_correlation": {},
            "communication_patterns": {},
            "temporal_correlations": {},
            "stress_propagation": {},
            "insights": [],
            "risk_score": 0
        }
        
        # Analyze incident-code correlations
        if incidents and github_data:
            correlations["incident_code_correlation"] = self._correlate_incidents_code(
                incidents, github_data
            )
        
        # Analyze communication patterns around incidents
        if incidents and slack_data:
            correlations["communication_patterns"] = self._correlate_incidents_communication(
                incidents, slack_data
            )
        
        # Analyze temporal patterns across platforms
        correlations["temporal_correlations"] = self._analyze_temporal_patterns(
            incidents, github_data, slack_data
        )
        
        # Analyze stress propagation patterns
        correlations["stress_propagation"] = self._analyze_stress_propagation(
            incidents, github_data, slack_data
        )
        
        # Generate insights and calculate risk score
        correlations = self._generate_insights(correlations)
        
        logger.info(f"Cross-platform correlation - Risk score: {correlations['risk_score']}, Insights: {len(correlations['insights'])}")
        
        return correlations
    
    def _correlate_incidents_code(self, incidents: List[Dict], github_data: Dict) -> Dict[str, Any]:
        """Find correlations between incidents and code activity."""
        correlation_data = {
            "commits_before_incidents": 0,
            "commits_after_incidents": 0,
            "hotfix_pattern": False,
            "incident_trigger_commits": [],
            "avg_time_to_fix": None
        }
        
        commits = github_data.get("commits", [])
        if not commits or not incidents:
            return correlation_data
        
        # Convert to datetime objects for comparison
        incident_times = []
        for incident in incidents:
            if incident.get("created_at"):
                incident_times.append(
                    datetime.fromisoformat(incident["created_at"].replace('Z', '+00:00'))
                )
        
        commit_times = []
        for commit in commits:
            timestamp = commit.get("timestamp") or commit.get("created_at")
            if timestamp:
                commit_times.append(
                    datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                )
        
        # Analyze commit patterns around incidents
        for incident_time in incident_times:
            # Check commits 24 hours before incident
            before_window = incident_time - timedelta(hours=24)
            commits_before = [ct for ct in commit_times if before_window <= ct < incident_time]
            correlation_data["commits_before_incidents"] += len(commits_before)
            
            # Check commits 24 hours after incident (potential fixes)
            after_window = incident_time + timedelta(hours=24)
            commits_after = [ct for ct in commit_times if incident_time < ct <= after_window]
            correlation_data["commits_after_incidents"] += len(commits_after)
            
            # Check for immediate commits (within 2 hours) that might have triggered incident
            trigger_window = incident_time - timedelta(hours=2)
            trigger_commits = [ct for ct in commit_times if trigger_window <= ct < incident_time]
            if trigger_commits:
                correlation_data["incident_trigger_commits"].append({
                    "incident_time": incident_time.isoformat(),
                    "commits_count": len(trigger_commits)
                })
        
        # Detect hotfix pattern (more commits after incidents than before)
        if correlation_data["commits_after_incidents"] > correlation_data["commits_before_incidents"] * 1.5:
            correlation_data["hotfix_pattern"] = True
        
        # Calculate average time to fix (time between incident and next commit)
        fix_times = []
        for incident_time in incident_times:
            next_commits = [ct for ct in commit_times if ct > incident_time]
            if next_commits:
                time_to_fix = (min(next_commits) - incident_time).total_seconds() / 3600  # hours
                fix_times.append(time_to_fix)
        
        if fix_times:
            correlation_data["avg_time_to_fix"] = round(statistics.mean(fix_times), 1)
        
        return correlation_data
    
    def _correlate_incidents_communication(self, incidents: List[Dict], slack_data: Dict) -> Dict[str, Any]:
        """Analyze communication patterns around incidents."""
        patterns = {
            "message_spike_during_incidents": False,
            "sentiment_drop_after_incidents": False,
            "after_hours_communication_increase": 0,
            "incident_communication_ratio": 0
        }
        
        messages = slack_data.get("messages", [])
        if not messages or not incidents:
            return patterns
        
        # Get incident time windows
        incident_windows = []
        for incident in incidents:
            if incident.get("created_at") and incident.get("resolved_at"):
                start = datetime.fromisoformat(incident["created_at"].replace('Z', '+00:00'))
                end = datetime.fromisoformat(incident["resolved_at"].replace('Z', '+00:00'))
                incident_windows.append((start, end))
        
        # Count messages during and outside incidents
        messages_during_incidents = 0
        messages_outside_incidents = 0
        sentiment_during = []
        sentiment_after = []
        
        for message in messages:
            msg_time = message.get("timestamp")
            if not msg_time:
                continue
                
            msg_dt = datetime.fromisoformat(msg_time.replace('Z', '+00:00'))
            msg_sentiment = message.get("sentiment", 0)
            
            # Check if message is during an incident
            during_incident = False
            for start, end in incident_windows:
                if start <= msg_dt <= end:
                    during_incident = True
                    messages_during_incidents += 1
                    sentiment_during.append(msg_sentiment)
                    break
                elif end < msg_dt <= end + timedelta(hours=24):
                    # Message within 24 hours after incident
                    sentiment_after.append(msg_sentiment)
            
            if not during_incident:
                messages_outside_incidents += 1
        
        # Calculate patterns
        total_messages = messages_during_incidents + messages_outside_incidents
        if total_messages > 0:
            patterns["incident_communication_ratio"] = round(
                messages_during_incidents / total_messages, 2
            )
        
        # Check for message spike (>2x normal rate)
        if incident_windows and messages_outside_incidents > 0:
            total_incident_hours = sum((end - start).total_seconds() / 3600 for start, end in incident_windows)
            incident_message_rate = messages_during_incidents / max(total_incident_hours, 1)
            
            # Approximate non-incident hours
            analysis_period_hours = 30 * 24  # Assuming 30-day analysis
            non_incident_hours = analysis_period_hours - total_incident_hours
            normal_message_rate = messages_outside_incidents / max(non_incident_hours, 1)
            
            if incident_message_rate > normal_message_rate * 2:
                patterns["message_spike_during_incidents"] = True
        
        # Check for sentiment drop after incidents
        if sentiment_during and sentiment_after:
            avg_during = statistics.mean(sentiment_during)
            avg_after = statistics.mean(sentiment_after)
            if avg_after < avg_during - 0.2:  # Significant drop
                patterns["sentiment_drop_after_incidents"] = True
        
        return patterns
    
    def _analyze_temporal_patterns(
        self, 
        incidents: List[Dict], 
        github_data: Dict, 
        slack_data: Dict
    ) -> Dict[str, Any]:
        """Analyze temporal patterns across all platforms."""
        patterns = {
            "weekend_activity_correlation": 0,
            "after_hours_correlation": 0,
            "peak_stress_hours": [],
            "cascade_pattern": False
        }
        
        # Collect all timestamped events
        all_events = []
        
        # Add incidents
        for incident in incidents:
            if incident.get("created_at"):
                all_events.append({
                    "time": datetime.fromisoformat(incident["created_at"].replace('Z', '+00:00')),
                    "type": "incident",
                    "severity": incident.get("severity", "unknown")
                })
        
        # Add commits
        for commit in github_data.get("commits", []):
            timestamp = commit.get("timestamp") or commit.get("created_at")
            if timestamp:
                all_events.append({
                    "time": datetime.fromisoformat(timestamp.replace('Z', '+00:00')),
                    "type": "commit"
                })
        
        # Add messages
        for message in slack_data.get("messages", []):
            if message.get("timestamp"):
                all_events.append({
                    "time": datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00')),
                    "type": "message",
                    "sentiment": message.get("sentiment", 0)
                })
        
        if not all_events:
            return patterns
        
        # Sort events by time
        all_events.sort(key=lambda x: x["time"])
        
        # Analyze weekend activity correlation
        weekend_incidents = sum(1 for e in all_events if e["type"] == "incident" and e["time"].weekday() >= 5)
        weekend_commits = sum(1 for e in all_events if e["type"] == "commit" and e["time"].weekday() >= 5)
        weekend_messages = sum(1 for e in all_events if e["type"] == "message" and e["time"].weekday() >= 5)
        
        total_weekend_activity = weekend_incidents + weekend_commits + weekend_messages
        if len(all_events) > 0:
            patterns["weekend_activity_correlation"] = round(total_weekend_activity / len(all_events), 2)
        
        # Analyze after-hours correlation (10 PM - 6 AM)
        after_hours_events = [
            e for e in all_events 
            if e["time"].hour >= 22 or e["time"].hour < 6
        ]
        if len(all_events) > 0:
            patterns["after_hours_correlation"] = round(len(after_hours_events) / len(all_events), 2)
        
        # Find peak stress hours
        hour_stress_scores = {}
        for event in all_events:
            hour = event["time"].hour
            score = hour_stress_scores.get(hour, 0)
            
            # Weight events by type
            if event["type"] == "incident":
                score += 3  # Incidents are high stress
            elif event["type"] == "commit" and (hour >= 22 or hour < 6):
                score += 2  # Late night commits indicate stress
            elif event["type"] == "message" and event.get("sentiment", 0) < -0.1:
                score += 1  # Negative messages add stress
                
            hour_stress_scores[hour] = score
        
        # Get top 3 stress hours
        if hour_stress_scores:
            sorted_hours = sorted(hour_stress_scores.items(), key=lambda x: x[1], reverse=True)
            patterns["peak_stress_hours"] = [hour for hour, _ in sorted_hours[:3]]
        
        # Detect cascade pattern (incident -> flurry of activity)
        cascade_events = 0
        for i, event in enumerate(all_events):
            if event["type"] == "incident":
                # Check for activity burst in next 2 hours
                incident_time = event["time"]
                burst_window = incident_time + timedelta(hours=2)
                
                subsequent_events = [
                    e for e in all_events[i+1:] 
                    if e["time"] <= burst_window
                ]
                
                if len(subsequent_events) >= 5:  # 5+ events in 2 hours after incident
                    cascade_events += 1
        
        if incidents and cascade_events > len(incidents) * 0.3:
            patterns["cascade_pattern"] = True
        
        return patterns
    
    def _analyze_stress_propagation(
        self, 
        incidents: List[Dict], 
        github_data: Dict, 
        slack_data: Dict
    ) -> Dict[str, Any]:
        """Analyze how stress propagates across platforms."""
        propagation = {
            "incident_to_code_stress": False,
            "code_to_communication_stress": False,
            "communication_to_incident_cycle": False,
            "stress_amplification_factor": 1.0
        }
        
        # Check incident -> code stress (rushed commits after incidents)
        if incidents and github_data.get("commits"):
            commits_after_incidents = 0
            rushed_commits = 0
            
            for incident in incidents:
                if incident.get("created_at"):
                    incident_time = datetime.fromisoformat(incident["created_at"].replace('Z', '+00:00'))
                    
                    # Check commits within 24 hours after incident
                    for commit in github_data["commits"]:
                        commit_time_str = commit.get("timestamp") or commit.get("created_at")
                        if commit_time_str:
                            commit_time = datetime.fromisoformat(commit_time_str.replace('Z', '+00:00'))
                            
                            if incident_time < commit_time <= incident_time + timedelta(hours=24):
                                commits_after_incidents += 1
                                
                                # Check if commit message indicates rush/stress
                                message = commit.get("message", "").lower()
                                if any(word in message for word in ["fix", "hotfix", "urgent", "asap", "emergency"]):
                                    rushed_commits += 1
            
            if commits_after_incidents > 0 and rushed_commits / commits_after_incidents > 0.5:
                propagation["incident_to_code_stress"] = True
        
        # Check code -> communication stress (negative sentiment after late commits)
        if github_data.get("commits") and slack_data.get("messages"):
            late_commits = [
                c for c in github_data["commits"]
                if c.get("timestamp") or c.get("created_at")
            ]
            
            for commit in late_commits:
                commit_time_str = commit.get("timestamp") or commit.get("created_at")
                commit_time = datetime.fromisoformat(commit_time_str.replace('Z', '+00:00'))
                
                # Check if late night commit
                if commit_time.hour >= 22 or commit_time.hour < 4:
                    # Look for messages in next 12 hours
                    messages_after = []
                    for message in slack_data["messages"]:
                        if message.get("timestamp"):
                            msg_time = datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))
                            if commit_time < msg_time <= commit_time + timedelta(hours=12):
                                messages_after.append(message.get("sentiment", 0))
                    
                    if messages_after and statistics.mean(messages_after) < -0.1:
                        propagation["code_to_communication_stress"] = True
                        break
        
        # Check communication -> incident cycle
        if slack_data.get("messages") and incidents:
            # Look for negative sentiment bursts followed by incidents
            negative_bursts = []
            messages = sorted(
                [m for m in slack_data["messages"] if m.get("timestamp")],
                key=lambda x: x["timestamp"]
            )
            
            # Find negative sentiment bursts (3+ negative messages in a row)
            for i in range(len(messages) - 2):
                sentiments = [
                    messages[i].get("sentiment", 0),
                    messages[i+1].get("sentiment", 0),
                    messages[i+2].get("sentiment", 0)
                ]
                
                if all(s < -0.1 for s in sentiments):
                    burst_time = datetime.fromisoformat(messages[i+2]["timestamp"].replace('Z', '+00:00'))
                    negative_bursts.append(burst_time)
            
            # Check if incidents follow negative bursts
            incidents_after_bursts = 0
            for burst_time in negative_bursts:
                for incident in incidents:
                    if incident.get("created_at"):
                        incident_time = datetime.fromisoformat(incident["created_at"].replace('Z', '+00:00'))
                        if burst_time < incident_time <= burst_time + timedelta(hours=48):
                            incidents_after_bursts += 1
                            break
            
            if negative_bursts and incidents_after_bursts / len(negative_bursts) > 0.3:
                propagation["communication_to_incident_cycle"] = True
        
        # Calculate stress amplification factor
        stress_factors = [
            propagation["incident_to_code_stress"],
            propagation["code_to_communication_stress"],
            propagation["communication_to_incident_cycle"]
        ]
        
        propagation["stress_amplification_factor"] = 1.0 + (sum(stress_factors) * 0.5)
        
        return propagation
    
    def _generate_insights(self, correlations: Dict[str, Any]) -> Dict[str, Any]:
        """Generate insights and calculate risk score based on correlations."""
        insights = []
        risk_score = 0
        
        # Incident-code correlation insights
        incident_code = correlations.get("incident_code_correlation", {})
        if incident_code.get("hotfix_pattern"):
            insights.append("Reactive development pattern detected: more commits after incidents than before")
            risk_score += 20
        
        if incident_code.get("incident_trigger_commits"):
            insights.append(f"Found {len(incident_code['incident_trigger_commits'])} potential incident-triggering deployments")
            risk_score += 15
        
        if incident_code.get("avg_time_to_fix") and incident_code["avg_time_to_fix"] < 2:
            insights.append("Very fast incident response times may indicate high pressure")
            risk_score += 10
        
        # Communication pattern insights
        comm_patterns = correlations.get("communication_patterns", {})
        if comm_patterns.get("message_spike_during_incidents"):
            insights.append("Communication volume spikes significantly during incidents")
            risk_score += 15
        
        if comm_patterns.get("sentiment_drop_after_incidents"):
            insights.append("Team sentiment drops after incident resolution, indicating stress")
            risk_score += 20
        
        # Temporal correlation insights
        temporal = correlations.get("temporal_correlations", {})
        if temporal.get("weekend_activity_correlation", 0) > 0.2:
            insights.append("High weekend activity across all platforms indicates poor work-life balance")
            risk_score += 25
        
        if temporal.get("after_hours_correlation", 0) > 0.3:
            insights.append("Significant after-hours activity correlation across platforms")
            risk_score += 20
        
        if temporal.get("cascade_pattern"):
            insights.append("Cascade pattern detected: incidents trigger flurries of activity")
            risk_score += 15
        
        # Stress propagation insights
        propagation = correlations.get("stress_propagation", {})
        if propagation.get("incident_to_code_stress"):
            insights.append("Incidents lead to rushed code changes")
            risk_score += 15
        
        if propagation.get("code_to_communication_stress"):
            insights.append("Late-night coding correlates with negative team communication")
            risk_score += 20
        
        if propagation.get("communication_to_incident_cycle"):
            insights.append("Negative team sentiment may be contributing to incident frequency")
            risk_score += 25
        
        if propagation.get("stress_amplification_factor", 1.0) > 1.5:
            insights.append("Stress is amplifying across platforms, creating a feedback loop")
            risk_score += 30
        
        correlations["insights"] = insights
        correlations["risk_score"] = min(risk_score, 100)  # Cap at 100
        
        return correlations


def create_cross_platform_correlator_tool():
    """Factory function to create cross-platform correlator tool for smolagents."""
    return CrossPlatformCorrelatorTool()