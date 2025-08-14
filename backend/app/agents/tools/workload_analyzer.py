"""
Workload Analysis Tool for Burnout Detection Agent
"""
from typing import Dict, List, Any, Optional
import statistics
import logging
from datetime import datetime, timedelta

try:
    from smolagents import BaseTool
except ImportError:
    # Fallback for development/testing when smolagents not available
    class BaseTool:
        def __init__(self, name, description):
            self.name = name
            self.description = description

logger = logging.getLogger(__name__)


class WorkloadAnalyzerTool(BaseTool):
    """Tool for analyzing workload distribution and intensity."""
    
    def __init__(self):
        try:
            # Try the smolagents BaseTool signature
            super().__init__()
            self.name = "workload_analyzer"
            self.description = "Analyzes workload distribution across time periods to identify unsustainable patterns"
        except TypeError:
            # Fallback to our custom BaseTool signature  
            super().__init__(
                name="workload_analyzer",
                description="Analyzes workload distribution across time periods to identify unsustainable patterns"
            )
    
    def __call__(self, user_data: Dict[str, Any], team_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analyze individual workload in context of team and sustainable levels.
        
        Args:
            user_data: Dictionary containing user's activity data
            team_context: Optional team statistics for comparison
            
        Returns:
            Dictionary with workload analysis results
        """
        if not user_data:
            return {
                "workload_status": "unknown",
                "intensity_score": 0,
                "sustainability_indicators": [],
                "recommendations": ["No data available for analysis"],
                "comparison_to_team": "unknown"
            }
        
        # Extract metrics from user data
        incidents = user_data.get('incidents', [])
        commits = user_data.get('commits', [])
        prs = user_data.get('pull_requests', [])
        messages = user_data.get('messages', [])
        
        # Calculate workload intensity
        intensity_metrics = self._calculate_intensity_metrics(user_data)
        
        # Analyze sustainability
        sustainability_indicators = self._analyze_sustainability(user_data, intensity_metrics)
        
        # Generate recommendations
        recommendations = self._generate_workload_recommendations(intensity_metrics, sustainability_indicators)
        
        # Team comparison if available
        team_comparison = self._compare_to_team(intensity_metrics, team_context) if team_context else "No team data available"
        
        # Determine overall workload status
        workload_status = self._determine_workload_status(intensity_metrics, sustainability_indicators)
        
        # Log detailed workload analysis results
        intensity_score = intensity_metrics.get('overall_intensity', 0)
        incident_count = len(user_data.get('incidents', []))
        logger.info(f"Workload Analysis Complete - Status: {workload_status}, Intensity: {intensity_score:.2f}, Incidents: {incident_count}, Sustainability indicators: {len(sustainability_indicators)}")
        
        return {
            "workload_status": workload_status,
            "intensity_score": intensity_score,
            "metrics": intensity_metrics,
            "sustainability_indicators": sustainability_indicators,
            "recommendations": recommendations,
            "comparison_to_team": team_comparison
        }
    
    def _calculate_intensity_metrics(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate various workload intensity metrics."""
        metrics = {}
        
        # Incident workload
        incidents = user_data.get('incidents', [])
        metrics['incident_count'] = len(incidents)
        metrics['incidents_per_day'] = len(incidents) / 30 if incidents else 0
        
        # Critical incident involvement
        critical_incidents = [i for i in incidents if i.get('severity') in ['critical', 'high', 'sev1', 'p1']]
        metrics['critical_incident_count'] = len(critical_incidents)
        metrics['critical_incident_rate'] = len(critical_incidents) / len(incidents) if incidents else 0
        
        # Response time pressure
        response_times = [i.get('response_time_minutes', 0) for i in incidents if 'response_time_minutes' in i]
        if response_times:
            avg_response = statistics.mean(response_times)
            metrics['avg_response_time'] = avg_response
            metrics['response_pressure'] = "high" if avg_response < 5 else "medium" if avg_response < 15 else "low"
        else:
            metrics['avg_response_time'] = 0
            metrics['response_pressure'] = "unknown"
        
        # Code activity workload
        commits = user_data.get('commits', [])
        prs = user_data.get('pull_requests', [])
        
        metrics['commit_count'] = len(commits)
        metrics['commits_per_day'] = len(commits) / 30 if commits else 0
        metrics['pr_count'] = len(prs)
        metrics['prs_per_week'] = len(prs) / 4.3 if prs else 0  # ~4.3 weeks in a month
        
        # Large code changes (complexity indicator)
        large_commits = [c for c in commits if c.get('changes', 0) > 500]
        large_prs = [pr for pr in prs if pr.get('size', 0) > 1000]
        
        metrics['large_commit_rate'] = len(large_commits) / len(commits) if commits else 0
        metrics['large_pr_rate'] = len(large_prs) / len(prs) if prs else 0
        
        # Communication workload
        messages = user_data.get('messages', [])
        metrics['message_count'] = len(messages)
        metrics['messages_per_day'] = len(messages) / 30 if messages else 0
        
        # After-hours and weekend work
        after_hours_activities = self._count_after_hours_activities(user_data)
        weekend_activities = self._count_weekend_activities(user_data)
        
        total_activities = metrics['incident_count'] + metrics['commit_count'] + metrics['message_count']
        
        metrics['after_hours_rate'] = after_hours_activities / total_activities if total_activities else 0
        metrics['weekend_rate'] = weekend_activities / total_activities if total_activities else 0
        
        # Calculate overall intensity score (0-100)
        intensity_factors = [
            min(metrics['incidents_per_day'] * 10, 30),  # Max 30 points for incidents
            min(metrics['commits_per_day'] * 2, 20),     # Max 20 points for commits
            min(metrics['messages_per_day'] * 0.5, 15), # Max 15 points for messages
            metrics['after_hours_rate'] * 20,           # Max 20 points for after-hours
            metrics['weekend_rate'] * 15                # Max 15 points for weekends
        ]
        
        metrics['overall_intensity'] = min(sum(intensity_factors), 100)
        
        return metrics
    
    def _count_after_hours_activities(self, user_data: Dict[str, Any]) -> int:
        """Count activities outside normal business hours (6 PM - 8 AM)."""
        count = 0
        
        for data_type in ['incidents', 'commits', 'messages']:
            for item in user_data.get(data_type, []):
                if 'timestamp' in item or 'created_at' in item:
                    timestamp = item.get('timestamp') or item.get('created_at')
                    try:
                        if isinstance(timestamp, str):
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(timestamp)
                        
                        # After hours: before 8 AM or after 6 PM
                        if dt.hour < 8 or dt.hour >= 18:
                            count += 1
                    except (ValueError, TypeError):
                        continue
        
        return count
    
    def _count_weekend_activities(self, user_data: Dict[str, Any]) -> int:
        """Count activities on weekends."""
        count = 0
        
        for data_type in ['incidents', 'commits', 'messages']:
            for item in user_data.get(data_type, []):
                if 'timestamp' in item or 'created_at' in item:
                    timestamp = item.get('timestamp') or item.get('created_at')
                    try:
                        if isinstance(timestamp, str):
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        else:
                            dt = datetime.fromtimestamp(timestamp)
                        
                        # Weekend: Saturday (5) or Sunday (6)
                        if dt.weekday() >= 5:
                            count += 1
                    except (ValueError, TypeError):
                        continue
        
        return count
    
    def _analyze_sustainability(self, user_data: Dict[str, Any], metrics: Dict[str, Any]) -> List[str]:
        """Analyze sustainability indicators."""
        indicators = []
        
        # High incident load
        if metrics['incidents_per_day'] > 2:
            indicators.append(f"Unsustainable incident load: {metrics['incidents_per_day']:.1f} per day")
        
        # High critical incident involvement
        if metrics['critical_incident_rate'] > 0.5 and metrics['critical_incident_count'] > 5:
            indicators.append(f"High critical incident involvement: {metrics['critical_incident_rate']:.1%}")
        
        # Excessive coding activity
        if metrics['commits_per_day'] > 10:
            indicators.append(f"Excessive coding frequency: {metrics['commits_per_day']:.1f} commits per day")
        
        # High after-hours work
        if metrics['after_hours_rate'] > 0.3:
            indicators.append(f"High after-hours work: {metrics['after_hours_rate']:.1%} of activities")
        
        # High weekend work
        if metrics['weekend_rate'] > 0.2:
            indicators.append(f"High weekend work: {metrics['weekend_rate']:.1%} of activities")
        
        # Response time pressure
        if metrics['response_pressure'] == "high":
            indicators.append(f"High response time pressure: avg {metrics['avg_response_time']:.1f} minutes")
        
        # Communication overload
        if metrics['messages_per_day'] > 50:
            indicators.append(f"Communication overload: {metrics['messages_per_day']:.1f} messages per day")
        
        # Large change frequency (indicates rushed work)
        if metrics['large_commit_rate'] > 0.4:
            indicators.append(f"High frequency of large commits: {metrics['large_commit_rate']:.1%}")
        
        if metrics['large_pr_rate'] > 0.3:
            indicators.append(f"High frequency of large PRs: {metrics['large_pr_rate']:.1%}")
        
        return indicators
    
    def _generate_workload_recommendations(self, metrics: Dict[str, Any], indicators: List[str]) -> List[str]:
        """Generate workload management recommendations."""
        recommendations = []
        
        # High-level recommendations based on intensity
        intensity = metrics.get('overall_intensity', 0)
        
        if intensity > 80:
            recommendations.append("URGENT: Workload reduction needed immediately to prevent burnout")
        elif intensity > 60:
            recommendations.append("Workload review recommended - consider delegation or prioritization")
        elif intensity > 40:
            recommendations.append("Monitor workload trends - some optimization may be beneficial")
        
        # Specific recommendations based on indicators
        if metrics.get('after_hours_rate', 0) > 0.3:
            recommendations.append("Establish clear boundaries for after-hours work")
        
        if metrics.get('weekend_rate', 0) > 0.2:
            recommendations.append("Reduce weekend work commitments for better recovery")
        
        if metrics.get('incidents_per_day', 0) > 2:
            recommendations.append("Consider improving incident prevention or expanding on-call rotation")
        
        if metrics.get('response_pressure') == "high":
            recommendations.append("Review response time expectations - current pressure may be unsustainable")
        
        if metrics.get('commits_per_day', 0) > 10:
            recommendations.append("Consider work breakdown - frequent small commits may indicate task switching overhead")
        
        if metrics.get('messages_per_day', 0) > 50:
            recommendations.append("Communication optimization - consider batching or async methods")
        
        # General recommendations
        if len(indicators) > 3:
            recommendations.append("Multiple sustainability concerns identified - comprehensive workload audit recommended")
        
        if not recommendations:
            recommendations.append("Workload appears sustainable - continue monitoring trends")
        
        return recommendations
    
    def _compare_to_team(self, metrics: Dict[str, Any], team_context: Dict[str, Any]) -> str:
        """Compare individual metrics to team averages."""
        comparisons = []
        
        # Compare incident load
        team_avg_incidents = team_context.get('avg_incidents_per_day', 0)
        user_incidents = metrics.get('incidents_per_day', 0)
        
        if team_avg_incidents > 0:
            ratio = user_incidents / team_avg_incidents
            if ratio > 1.5:
                comparisons.append(f"Incident load {ratio:.1f}x higher than team average")
            elif ratio < 0.5:
                comparisons.append(f"Incident load {ratio:.1f}x lower than team average")
            else:
                comparisons.append("Incident load similar to team average")
        
        # Compare coding activity
        team_avg_commits = team_context.get('avg_commits_per_day', 0)
        user_commits = metrics.get('commits_per_day', 0)
        
        if team_avg_commits > 0:
            ratio = user_commits / team_avg_commits
            if ratio > 1.5:
                comparisons.append(f"Coding activity {ratio:.1f}x higher than team average")
            elif ratio < 0.5:
                comparisons.append(f"Coding activity {ratio:.1f}x lower than team average")
        
        # Compare after-hours work
        team_avg_after_hours = team_context.get('avg_after_hours_rate', 0)
        user_after_hours = metrics.get('after_hours_rate', 0)
        
        if team_avg_after_hours > 0:
            if user_after_hours > team_avg_after_hours * 1.3:
                comparisons.append("After-hours work significantly above team average")
            elif user_after_hours < team_avg_after_hours * 0.7:
                comparisons.append("After-hours work below team average")
        
        return "; ".join(comparisons) if comparisons else "Limited team comparison data available"
    
    def _determine_workload_status(self, metrics: Dict[str, Any], indicators: List[str]) -> str:
        """Determine overall workload status."""
        intensity = metrics.get('overall_intensity', 0)
        indicator_count = len(indicators)
        
        if intensity > 80 or indicator_count > 4:
            return "critical"
        elif intensity > 60 or indicator_count > 2:
            return "high"
        elif intensity > 40 or indicator_count > 0:
            return "moderate"
        else:
            return "sustainable"


def create_workload_analyzer_tool():
    """Factory function to create workload analyzer tool for smolagents."""
    return WorkloadAnalyzerTool()