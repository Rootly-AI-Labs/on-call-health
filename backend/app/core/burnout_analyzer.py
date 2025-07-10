"""
Burnout risk analysis engine based on Christina Maslach's research.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List
import pytz

logger = logging.getLogger(__name__)


class BurnoutAnalyzer:
    """Analyzes incident data to calculate burnout risk scores."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.thresholds = config.get("burnout_thresholds", {})
        self.scoring = config.get("scoring", {})
        self.analysis_config = config.get("analysis", {})
        
    def analyze_user_burnout(
        self, 
        user: Dict[str, Any], 
        user_incidents: List[str],
        all_incidents: List[Dict[str, Any]],
        github_activity: Dict[str, Any] = None,
        slack_activity: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Calculate comprehensive burnout risk for a single user."""
        
        # Filter incidents for this user
        incidents = [inc for inc in all_incidents if inc["id"] in user_incidents]
        
        if not incidents:
            return self._create_empty_analysis(user)
        
        # Calculate the three Maslach dimensions
        emotional_exhaustion = self._calculate_emotional_exhaustion(user, incidents, github_activity, slack_activity)
        depersonalization = self._calculate_depersonalization(user, incidents, github_activity, slack_activity)
        personal_accomplishment = self._calculate_personal_accomplishment(user, incidents, github_activity, slack_activity)
        
        # Calculate overall burnout score
        weights = self.scoring
        # Ensure personal accomplishment score is capped at 10 to prevent negative overall scores
        pa_score = min(10, max(0, personal_accomplishment["score"]))
        overall_score = (
            emotional_exhaustion["score"] * weights.get("emotional_exhaustion_weight", 0.4) +
            depersonalization["score"] * weights.get("depersonalization_weight", 0.3) +
            (10 - pa_score) * weights.get("personal_accomplishment_weight", 0.3)
        )
        
        # Ensure overall score is never negative
        overall_score = max(0, overall_score)
        
        # Calculate data source contributions to the overall score
        has_github = github_activity and self.config.get('github_integration', {}).get('enabled', False)
        has_slack = slack_activity and self.config.get('slack_integration', {}).get('enabled', False)
        
        # Calculate weighted contributions
        incident_contribution = 0
        github_contribution = 0
        slack_contribution = 0
        
        if has_github and has_slack:
            # All three sources: 70% incident, 15% github, 15% slack
            incident_contribution = overall_score * 0.7
            github_contribution = overall_score * 0.15
            slack_contribution = overall_score * 0.15
        elif has_github:
            # Incident + GitHub: 85% incident, 15% github
            incident_contribution = overall_score * 0.85
            github_contribution = overall_score * 0.15
        elif has_slack:
            # Incident + Slack: 85% incident, 15% slack
            incident_contribution = overall_score * 0.85
            slack_contribution = overall_score * 0.15
        else:
            # Incident only: 100% incident
            incident_contribution = overall_score
        
        # Determine risk level
        risk_level = self._determine_risk_level(overall_score)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            emotional_exhaustion, depersonalization, personal_accomplishment
        )
        
        result = {
            "user_id": user["id"],
            "user_name": user["name"],
            "user_email": user["email"],
            "analysis_period": {
                "days": self.analysis_config.get("days_to_analyze", 30),
                "incident_count": len(incidents)
            },
            "burnout_score": round(overall_score, 2),
            "risk_level": risk_level,
            "dimensions": {
                "emotional_exhaustion": emotional_exhaustion,
                "depersonalization": depersonalization,
                "personal_accomplishment": personal_accomplishment
            },
            "key_metrics": self._calculate_key_metrics(user, incidents),
            "recommendations": recommendations,
            "analysis_timestamp": datetime.now().isoformat()
        }
        
        # Add data source contributions
        if has_github or has_slack:
            result["data_source_contributions"] = {
                "incident": round(incident_contribution, 2),
                "github": round(github_contribution, 2),
                "slack": round(slack_contribution, 2)
            }
        
        return result
    
    def _calculate_emotional_exhaustion(
        self, 
        user: Dict[str, Any], 
        incidents: List[Dict[str, Any]],
        github_activity: Dict[str, Any] = None,
        slack_activity: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Calculate emotional exhaustion indicators."""
        
        # Incident frequency
        days = self.analysis_config.get("days_to_analyze", 30)
        incidents_per_week = (len(incidents) / days) * 7
        
        # After-hours incidents
        after_hours_count = self._count_after_hours_incidents(user, incidents)
        after_hours_percentage = after_hours_count / len(incidents) if incidents else 0
        
        # Average resolution time
        resolution_times = [
            inc["duration_minutes"] for inc in incidents 
            if inc["duration_minutes"] is not None
        ]
        avg_resolution_hours = (
            sum(resolution_times) / len(resolution_times) / 60 
            if resolution_times else 0
        )
        
        # Incident clustering (incidents within 4 hours of each other)
        clustered_incidents = self._count_clustered_incidents(incidents)
        
        # Severity-weighted workload
        severity_weight = self._calculate_severity_weighted_load(incidents)
        
        # Score calculation (0-10 scale)
        frequency_score = min(10, incidents_per_week / 
                            self.thresholds.get("incidents_per_week_high", 10) * 10)
        after_hours_score = min(10, after_hours_percentage / 
                              self.thresholds.get("after_hours_percentage_high", 0.3) * 10)
        duration_score = min(10, avg_resolution_hours / 
                           self.thresholds.get("avg_resolution_time_hours_high", 4) * 10)
        cluster_score = min(10, clustered_incidents / len(incidents) * 20) if incidents else 0
        
        # GitHub metrics integration (if available)
        github_score = 0
        github_indicators = {}
        if github_activity and self.config.get('github_integration', {}).get('enabled', False):
            github_metrics = github_activity.get('metrics', {})
            
            # After-hours coding work contributes to exhaustion
            github_after_hours_pct = github_metrics.get('after_hours_commit_percentage', 0)
            github_weekend_pct = github_metrics.get('weekend_commit_percentage', 0)
            github_clustered_commits = github_metrics.get('clustered_commits', 0)
            total_commits = github_metrics.get('total_commits', 0)
            
            # Calculate GitHub exhaustion indicators
            github_after_hours_score = min(10, github_after_hours_pct / 0.4 * 10)  # 40% threshold
            github_weekend_score = min(10, github_weekend_pct / 0.2 * 10)  # 20% threshold  
            github_cluster_ratio = (github_clustered_commits / total_commits) if total_commits > 0 else 0
            github_cluster_score = min(10, github_cluster_ratio * 15)  # Clustering indicates stress
            
            github_score = (github_after_hours_score + github_weekend_score + github_cluster_score) / 3
            github_indicators = {
                'github_after_hours_percentage': round(github_after_hours_pct, 2),
                'github_weekend_percentage': round(github_weekend_pct, 2),
                'github_clustered_commits_ratio': round(github_cluster_ratio, 2),
                'github_total_commits': total_commits
            }
        
        # Slack integration for emotional exhaustion
        slack_score = 0
        slack_indicators = {}
        if slack_activity and self.config.get('slack_integration', {}).get('enabled', False):
            from slack_analyzer import SlackAnalyzer
            slack_analyzer = SlackAnalyzer(self.config)
            slack_analysis = slack_analyzer.analyze_user_slack_activity(slack_activity)
            slack_score = slack_analysis.get('emotional_exhaustion', {}).get('score', 0)
            slack_indicators = slack_analysis.get('emotional_exhaustion', {}).get('indicators', {})
        
        # Combine scores with different data sources
        # Weight distribution: Incidents (50%), GitHub (25%), Slack (25%)
        has_github = github_activity and self.config.get('github_integration', {}).get('enabled', False)
        has_slack = slack_activity and self.config.get('slack_integration', {}).get('enabled', False)
        
        incident_component = (frequency_score + after_hours_score + duration_score + cluster_score) / 4
        
        if has_github and has_slack:
            overall_score = (incident_component * 0.5) + (github_score * 0.25) + (slack_score * 0.25)
        elif has_github:
            overall_score = (incident_component * 0.7) + (github_score * 0.3)
        elif has_slack:
            overall_score = (incident_component * 0.7) + (slack_score * 0.3)
        else:
            overall_score = incident_component
        
        indicators = {
            "incidents_per_week": round(incidents_per_week, 2),
            "after_hours_percentage": round(after_hours_percentage, 2),
            "avg_resolution_hours": round(avg_resolution_hours, 2),
            "clustered_incidents": clustered_incidents,
            "severity_weighted_load": round(severity_weight, 2)
        }
        
        # Add GitHub indicators if available
        if github_indicators:
            indicators.update(github_indicators)
        
        # Add Slack indicators if available
        if slack_indicators:
            slack_prefixed = {f"slack_{k}": v for k, v in slack_indicators.items()}
            indicators.update(slack_prefixed)
        
        return {
            "score": round(overall_score, 2),
            "indicators": indicators,
            "contributing_factors": self._identify_exhaustion_factors(
                frequency_score, after_hours_score, duration_score, cluster_score, github_score, slack_score
            )
        }
    
    def _calculate_depersonalization(
        self, 
        user: Dict[str, Any], 
        incidents: List[Dict[str, Any]],
        github_activity: Dict[str, Any] = None,
        slack_activity: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Calculate depersonalization indicators."""
        
        if not incidents:
            return {"score": 0, "indicators": {}, "contributing_factors": []}
        
        # Escalation frequency
        escalated_incidents = sum(1 for inc in incidents if len(inc.get("roles", [])) > 1)
        escalation_rate = escalated_incidents / len(incidents)
        
        # Solo incident handling (lack of collaboration)
        solo_incidents = sum(1 for inc in incidents if len(inc.get("roles", [])) <= 1)
        solo_rate = solo_incidents / len(incidents)
        
        # Response time degradation over time
        response_degradation = self._calculate_response_time_trend(incidents)
        
        # Resolution message length (shorter = more cynical)
        resolution_lengths = [
            len(inc.get("resolution_message") or "") for inc in incidents
            if inc.get("resolution_message")
        ]
        avg_resolution_length = sum(resolution_lengths) / len(resolution_lengths) if resolution_lengths else 0
        
        # Score calculation
        escalation_score = min(10, escalation_rate / 
                             self.thresholds.get("escalation_rate_high", 0.4) * 10)
        solo_score = min(10, solo_rate * 10)
        degradation_score = max(0, response_degradation * 10)  # Positive degradation = bad
        communication_score = max(0, 10 - (avg_resolution_length / 50))  # Shorter = worse
        
        # GitHub metrics for depersonalization (repository switching, reduced collaboration)
        github_score = 0
        github_indicators = {}
        if github_activity and self.config.get('github_integration', {}).get('enabled', False):
            github_metrics = github_activity.get('metrics', {})
            
            # Repository switching can indicate disengagement or scattered focus
            repos_touched = github_metrics.get('repositories_touched', 0)
            total_commits = github_metrics.get('total_commits', 0)
            total_prs = github_metrics.get('total_pull_requests', 0)
            
            # High repo switching relative to activity suggests scattered focus
            if total_commits > 0:
                repo_switching_ratio = repos_touched / total_commits
                repo_switching_score = min(10, repo_switching_ratio * 20)  # Higher = worse
            else:
                repo_switching_score = 0
                repo_switching_ratio = 0
            
            # Low PR creation relative to commits suggests reduced collaboration
            if total_commits > 0:
                pr_ratio = total_prs / total_commits
                collaboration_score = max(0, 10 - (pr_ratio * 30))  # Lower PR ratio = worse
            else:
                pr_ratio = 0
                collaboration_score = 5
            
            github_score = (repo_switching_score + collaboration_score) / 2
            github_indicators = {
                'github_repo_switching_ratio': round(repo_switching_ratio, 3),
                'github_pr_to_commit_ratio': round(pr_ratio, 3),
                'github_repositories_touched': repos_touched
            }
        
        # Combine scores
        if github_activity and self.config.get('github_integration', {}).get('enabled', False):
            incident_component = (escalation_score + solo_score + degradation_score + communication_score) / 4
            overall_score = (incident_component * 0.7) + (github_score * 0.3)
        else:
            overall_score = (escalation_score + solo_score + degradation_score + communication_score) / 4
        
        indicators = {
            "escalation_rate": round(escalation_rate, 2),
            "solo_incident_rate": round(solo_rate, 2),
            "response_time_trend": round(response_degradation, 2),
            "avg_resolution_message_length": round(avg_resolution_length, 1)
        }
        
        # Add GitHub indicators if available
        if github_indicators:
            indicators.update(github_indicators)
        
        return {
            "score": round(overall_score, 2),
            "indicators": indicators,
            "contributing_factors": self._identify_depersonalization_factors(
                escalation_score, solo_score, degradation_score, communication_score, github_score
            )
        }
    
    def _calculate_personal_accomplishment(
        self, 
        user: Dict[str, Any], 
        incidents: List[Dict[str, Any]],
        github_activity: Dict[str, Any] = None,
        slack_activity: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Calculate personal accomplishment indicators (higher score = better)."""
        
        if not incidents:
            return {"score": 5, "indicators": {}, "contributing_factors": []}
        
        # Resolution success rate
        resolved_incidents = sum(1 for inc in incidents if inc["status"] == "resolved")
        resolution_rate = resolved_incidents / len(incidents)
        
        # Time to resolution improvement
        resolution_improvement = self._calculate_resolution_time_improvement(incidents)
        
        # Incident complexity handling (higher severity = more accomplishment)
        complexity_score = self._calculate_complexity_handling_score(incidents)
        
        # Knowledge sharing (post-incident activities)
        knowledge_sharing_score = self._calculate_knowledge_sharing_score(incidents)
        
        # Score calculation (0-10 scale, higher = better accomplishment)
        success_score = resolution_rate * 10
        improvement_score = max(0, 10 + (resolution_improvement * 10))  # Negative improvement = good
        
        # GitHub metrics for personal accomplishment (productive activity, completed work)
        github_score = 5  # Default neutral score
        github_indicators = {}
        if github_activity and self.config.get('github_integration', {}).get('enabled', False):
            github_metrics = github_activity.get('metrics', {})
            
            # Regular productive activity indicates accomplishment
            commits_per_week = github_metrics.get('commits_per_week', 0)
            prs_per_week = github_metrics.get('prs_per_week', 0)
            total_commits = github_metrics.get('total_commits', 0)
            
            # Productive activity scoring (balanced workload is good)
            if commits_per_week > 0:
                # Sweet spot around 3-8 commits per week for sustainable productivity
                if 3 <= commits_per_week <= 8:
                    activity_score = 10
                elif commits_per_week < 3:
                    activity_score = (commits_per_week / 3) * 7  # Lower activity = lower accomplishment
                else:
                    activity_score = max(5, 10 - ((commits_per_week - 8) * 0.5))  # Excessive activity = potential burnout
            else:
                activity_score = 0
            
            # PR creation indicates collaborative accomplishment
            pr_score = min(10, prs_per_week * 5)  # 2 PRs per week = max score
            
            github_score = (activity_score + pr_score) / 2
            github_indicators = {
                'github_commits_per_week': round(commits_per_week, 2),
                'github_prs_per_week': round(prs_per_week, 2),
                'github_productivity_score': round(github_score, 2)
            }
        
        # Combine scores
        if github_activity and self.config.get('github_integration', {}).get('enabled', False):
            incident_component = (success_score + improvement_score + complexity_score + knowledge_sharing_score) / 4
            overall_score = (incident_component * 0.7) + (github_score * 0.3)
        else:
            overall_score = (success_score + improvement_score + complexity_score + knowledge_sharing_score) / 4
        
        indicators = {
            "resolution_success_rate": round(resolution_rate, 2),
            "resolution_time_improvement": round(resolution_improvement, 2),
            "complexity_handling_score": round(complexity_score, 2),
            "knowledge_sharing_score": round(knowledge_sharing_score, 2)
        }
        
        # Add GitHub indicators if available
        if github_indicators:
            indicators.update(github_indicators)
        
        return {
            "score": round(overall_score, 2),
            "indicators": indicators,
            "contributing_factors": self._identify_accomplishment_factors(
                success_score, improvement_score, complexity_score, knowledge_sharing_score, github_score
            )
        }
    
    def _count_after_hours_incidents(
        self, 
        user: Dict[str, Any], 
        incidents: List[Dict[str, Any]]
    ) -> int:
        """Count incidents that occurred outside business hours."""
        business_hours = self.analysis_config.get("business_hours", {"start": 9, "end": 17})
        user_timezone = user.get("timezone", "UTC")
        
        try:
            tz = pytz.timezone(user_timezone)
        except Exception:
            tz = pytz.UTC
        
        after_hours_count = 0
        
        for incident in incidents:
            created_at = incident.get("created_at")
            if not created_at:
                continue
            
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                local_dt = dt.astimezone(tz)
                
                hour = local_dt.hour
                is_weekend = local_dt.weekday() >= 5
                
                if (is_weekend or 
                    hour < business_hours["start"] or 
                    hour >= business_hours["end"]):
                    after_hours_count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing timestamp {created_at}: {e}")
        
        return after_hours_count
    
    def _count_clustered_incidents(self, incidents: List[Dict[str, Any]]) -> int:
        """Count incidents that occur within 4 hours of each other."""
        if len(incidents) < 2:
            return 0
        
        # Sort incidents by creation time
        sorted_incidents = sorted(
            incidents, 
            key=lambda x: x.get("created_at", "")
        )
        
        clustered = 0
        cluster_window_hours = 4
        
        for i in range(1, len(sorted_incidents)):
            try:
                prev_time = datetime.fromisoformat(
                    sorted_incidents[i-1].get("created_at", "").replace('Z', '+00:00')
                )
                curr_time = datetime.fromisoformat(
                    sorted_incidents[i].get("created_at", "").replace('Z', '+00:00')
                )
                
                if (curr_time - prev_time).total_seconds() <= cluster_window_hours * 3600:
                    clustered += 1
                    
            except Exception:
                continue
        
        return clustered
    
    def _calculate_severity_weighted_load(self, incidents: List[Dict[str, Any]]) -> float:
        """Calculate severity-weighted incident load."""
        weights = self.analysis_config.get("severity_weights", {
            "sev1": 3.0, "sev2": 2.0, "sev3": 1.5, "sev4": 1.0
        })
        
        total_weight = 0
        for incident in incidents:
            severity = incident.get("severity_name", "sev4").lower()
            weight = weights.get(severity, 1.0)
            total_weight += weight
        
        return total_weight
    
    def _calculate_response_time_trend(self, incidents: List[Dict[str, Any]]) -> float:
        """Calculate trend in response times (positive = getting worse)."""
        response_times = []
        
        for incident in incidents:
            if incident.get("time_to_acknowledge_minutes"):
                response_times.append((
                    incident.get("created_at", ""),
                    incident["time_to_acknowledge_minutes"]
                ))
        
        if len(response_times) < 3:
            return 0
        
        # Sort by time and calculate trend
        response_times.sort(key=lambda x: x[0])
        
        # Linear trend calculation
        n = len(response_times)
        recent_avg = sum(rt[1] for rt in response_times[-n//3:]) / (n//3)
        early_avg = sum(rt[1] for rt in response_times[:n//3]) / (n//3)
        
        # Normalize the trend (-1 to 1)
        if early_avg > 0:
            return (recent_avg - early_avg) / early_avg
        return 0
    
    def _calculate_resolution_time_improvement(self, incidents: List[Dict[str, Any]]) -> float:
        """Calculate improvement in resolution times (negative = improvement)."""
        resolution_times = []
        
        for incident in incidents:
            if incident.get("duration_minutes"):
                resolution_times.append((
                    incident.get("created_at", ""),
                    incident["duration_minutes"]
                ))
        
        if len(resolution_times) < 3:
            return 0
        
        # Sort by time and calculate trend
        resolution_times.sort(key=lambda x: x[0])
        
        n = len(resolution_times)
        recent_avg = sum(rt[1] for rt in resolution_times[-n//3:]) / (n//3)
        early_avg = sum(rt[1] for rt in resolution_times[:n//3]) / (n//3)
        
        if early_avg > 0:
            return (recent_avg - early_avg) / early_avg
        return 0
    
    def _calculate_complexity_handling_score(self, incidents: List[Dict[str, Any]]) -> float:
        """Score based on handling of complex/high-severity incidents."""
        severity_scores = {"sev1": 10, "sev2": 7, "sev3": 4, "sev4": 2}
        
        if not incidents:
            return 5
        
        total_score = 0
        for incident in incidents:
            severity = incident.get("severity_name", "sev4").lower()
            score = severity_scores.get(severity, 2)
            total_score += score
        
        return min(10, total_score / len(incidents))
    
    def _calculate_knowledge_sharing_score(self, incidents: List[Dict[str, Any]]) -> float:
        """Score based on post-incident documentation and sharing."""
        documented_incidents = 0
        
        for incident in incidents:
            resolution_message = incident.get("resolution_message") or ""
            summary = incident.get("summary") or ""
            
            # Consider an incident "documented" if it has substantial content
            if (len(resolution_message) > 50 or len(summary) > 50):
                documented_incidents += 1
        
        if not incidents:
            return 5
        
        documentation_rate = documented_incidents / len(incidents)
        return documentation_rate * 10
    
    def _determine_risk_level(self, score: float) -> str:
        """Determine risk level based on overall burnout score."""
        if score >= 7:
            return "high"
        elif score >= 4:
            return "medium"
        else:
            return "low"
    
    def _calculate_key_metrics(
        self, 
        user: Dict[str, Any], 
        incidents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Calculate key summary metrics."""
        if not incidents:
            return {}
        
        days = self.analysis_config.get("days_to_analyze", 30)
        
        return {
            "total_incidents": len(incidents),
            "incidents_per_week": round((len(incidents) / days) * 7, 2),
            "after_hours_incidents": self._count_after_hours_incidents(user, incidents),
            "avg_resolution_time_hours": round(
                sum(inc["duration_minutes"] for inc in incidents 
                    if inc["duration_minutes"]) / len(incidents) / 60, 2
            ) if any(inc["duration_minutes"] for inc in incidents) else 0,
            "resolution_success_rate": round(
                sum(1 for inc in incidents if inc["status"] == "resolved") / len(incidents), 2
            )
        }
    
    def _generate_recommendations(
        self, 
        emotional_exhaustion: Dict[str, Any], 
        depersonalization: Dict[str, Any], 
        personal_accomplishment: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Emotional exhaustion recommendations
        if emotional_exhaustion["score"] >= 7:
            recommendations.append("High workload detected. Consider redistributing incidents or adding team members.")
            
        if emotional_exhaustion["indicators"].get("after_hours_percentage", 0) > 0.2:
            recommendations.append("Frequent after-hours work detected. Review on-call rotation and coverage.")
        
        # Depersonalization recommendations
        if depersonalization["score"] >= 7:
            recommendations.append("Signs of disengagement detected. Consider pairing with team members and increasing collaboration.")
            
        if depersonalization["indicators"].get("escalation_rate", 0) > 0.3:
            recommendations.append("High escalation rate suggests need for additional training or support.")
        
        # Personal accomplishment recommendations
        if personal_accomplishment["score"] <= 3:
            recommendations.append("Low sense of accomplishment. Consider assigning more varied or challenging incidents.")
            recommendations.append("Provide recognition for successful incident resolutions.")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Overall burnout risk appears manageable. Continue monitoring.")
        
        return recommendations
    
    def _identify_exhaustion_factors(self, freq: float, after_hrs: float, duration: float, cluster: float, github_score: float = 0, slack_score: float = 0) -> List[str]:
        """Identify specific contributing factors to emotional exhaustion."""
        factors = []
        if freq >= 7: factors.append("High incident frequency")
        if after_hrs >= 7: factors.append("Excessive after-hours work")
        if duration >= 7: factors.append("Long resolution times")
        if cluster >= 7: factors.append("Incident clustering")
        if github_score >= 7: factors.append("High after-hours coding activity")
        if slack_score >= 7: factors.append("High Slack communication stress patterns")
        return factors
    
    def _identify_depersonalization_factors(self, esc: float, solo: float, deg: float, comm: float, github_score: float = 0) -> List[str]:
        """Identify specific contributing factors to depersonalization."""
        factors = []
        if esc >= 7: factors.append("High escalation rate")
        if solo >= 7: factors.append("Too many solo incidents")
        if deg >= 7: factors.append("Declining response times")
        if comm >= 7: factors.append("Poor communication patterns")
        if github_score >= 7: factors.append("Scattered repository focus or reduced code collaboration")
        return factors
    
    def _identify_accomplishment_factors(self, success: float, improve: float, complex: float, share: float, github_score: float = 5) -> List[str]:
        """Identify factors affecting personal accomplishment."""
        factors = []
        if success <= 3: factors.append("Low resolution success rate")
        if improve <= 3: factors.append("No improvement in resolution times")
        if complex <= 3: factors.append("Limited complex incident exposure")
        if share <= 3: factors.append("Minimal knowledge sharing")
        if github_score <= 3: factors.append("Low productive coding activity")
        return factors
    
    def _create_empty_analysis(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create analysis for user with no incidents."""
        return {
            "user_id": user["id"],
            "user_name": user["name"],
            "user_email": user["email"],
            "analysis_period": {
                "days": self.analysis_config.get("days_to_analyze", 30),
                "incident_count": 0
            },
            "burnout_score": 0,
            "risk_level": "low",
            "dimensions": {
                "emotional_exhaustion": {"score": 0, "indicators": {}, "contributing_factors": []},
                "depersonalization": {"score": 0, "indicators": {}, "contributing_factors": []},
                "personal_accomplishment": {"score": 5, "indicators": {}, "contributing_factors": []}
            },
            "key_metrics": {},
            "recommendations": ["No incidents in analysis period. User may not be actively on-call."],
            "analysis_timestamp": datetime.now().isoformat()
        }
    
