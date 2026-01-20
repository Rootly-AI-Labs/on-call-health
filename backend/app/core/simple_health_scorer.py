"""
Simple Health Scoring System - Honest, Transparent, and Data-Driven

This module replaces the OCB (Copenhagen Burnout Inventory) framework with a simple,
honest scoring system based on 3 categories of real data:

1. Self-Reported (40% weight) - Survey responses about feeling and workload
2. Incident Load (35% weight) - Actual incident frequency, severity, and response times
3. Work Timing (25% weight) - When work happens (after-hours, weekends, late night)

Key Principles:
- NO FAKE METRICS: Only use data we actually collect
- NO PROXIES: Don't pretend incident data represents vacation or sleep
- ADAPTIVE REWEIGHTING: When survey data missing, redistribute weights
- EVERYONE GETS A SCORE: Not just users with incidents
- TRANSPARENT: Always show what contributed to the score
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SimpleHealthScorer:
    """
    Calculate health scores based on real, collected data only.

    Scoring Model:
    - Self-Reported: 40% (survey: feeling + workload)
    - Incident Load: 35% (frequency, severity, after-hours %)
    - Work Timing: 25% (after-hours %, weekend %, late-night %)

    Adaptive Reweighting:
    - If survey missing: Incident Load 58%, Work Timing 42%
    - If GitHub missing: Self-Reported 62%, Incident Load 54% (no Work Timing)
    - If both missing: Incident Load 100%
    """

    # Default weights (sum to 100 for percentage-based scoring)
    DEFAULT_WEIGHTS = {
        'self_reported': 40,
        'incident_load': 35,
        'work_timing': 25
    }

    # Score interpretation ranges (0-100 scale, lower is better)
    SCORE_RANGES = {
        'healthy': (0, 25),      # 0-24: Healthy
        'fair': (25, 50),        # 25-49: Fair - mild signs of overwork
        'poor': (50, 75),        # 50-74: Poor - moderate signs of overwork
        'critical': (75, 100)    # 75-100: Critical - severe signs of overwork
    }

    def calculate_health_score(
        self,
        user_email: str,
        survey_data: Optional[Dict[str, Any]] = None,
        incident_data: Optional[Dict[str, Any]] = None,
        github_data: Optional[Dict[str, Any]] = None,
        time_range_days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive health score from available data.

        Args:
            user_email: User email for identification
            survey_data: Self-reported survey data (feeling_score, workload_score)
            incident_data: Incident response data (count, severity, timing)
            github_data: GitHub activity data (commits, timing)
            time_range_days: Analysis time range

        Returns:
            Dict with overall score, category breakdown, and transparency info
        """
        # Determine which data sources are available
        has_survey = survey_data is not None and 'feeling_score' in survey_data
        has_incidents = incident_data is not None and incident_data.get('total_incidents', 0) > 0
        has_github = github_data is not None and github_data.get('total_commits', 0) > 0

        # Calculate adaptive weights based on available data
        weights = self._calculate_adaptive_weights(has_survey, has_incidents, has_github)

        # Calculate category scores (0-100 scale, higher = worse)
        category_scores = {}
        category_details = {}

        # 1. Self-Reported Score
        if has_survey:
            score, details = self._calculate_self_reported_score(survey_data)
            category_scores['self_reported'] = score
            category_details['self_reported'] = details

        # 2. Incident Load Score
        if has_incidents:
            score, details = self._calculate_incident_load_score(incident_data, time_range_days)
            category_scores['incident_load'] = score
            category_details['incident_load'] = details
        else:
            # Everyone gets 0 for incident load if no incidents (healthy state)
            category_scores['incident_load'] = 0
            category_details['incident_load'] = {
                'score': 0,
                'total_incidents': 0,
                'incidents_per_week': 0,
                'after_hours_percentage': 0,
                'avg_response_minutes': 0,
                'explanation': 'No incidents in this period - healthy state'
            }

        # 3. Work Timing Score
        if has_github:
            score, details = self._calculate_work_timing_score(github_data, incident_data)
            category_scores['work_timing'] = score
            category_details['work_timing'] = details
        elif has_incidents:
            # Use incident timing as fallback if no GitHub data
            score, details = self._calculate_work_timing_from_incidents(incident_data)
            category_scores['work_timing'] = score
            category_details['work_timing'] = details
        else:
            # No timing data available
            category_scores['work_timing'] = 0
            category_details['work_timing'] = {
                'score': 0,
                'after_hours_percentage': 0,
                'weekend_percentage': 0,
                'late_night_percentage': 0,
                'explanation': 'No timing data available'
            }

        # Calculate weighted overall score
        overall_score = 0
        weighted_contributions = {}

        for category, weight in weights.items():
            if category in category_scores:
                category_score = category_scores[category]
                contribution = (category_score * weight) / 100
                weighted_contributions[category] = {
                    'raw_score': category_score,
                    'weight': weight,
                    'contribution': contribution,
                    'max_contribution': weight  # Maximum possible contribution
                }
                overall_score += contribution

        # Get interpretation
        interpretation = self._get_interpretation(overall_score)

        return {
            'overall_score': round(overall_score, 1),
            'interpretation': interpretation,
            'category_scores': category_scores,
            'category_details': category_details,
            'weighted_contributions': weighted_contributions,
            'weights_used': weights,
            'data_sources': {
                'has_survey': has_survey,
                'has_incidents': has_incidents,
                'has_github': has_github
            },
            'transparency': self._generate_transparency_message(has_survey, has_incidents, has_github, weights),
            'user_email': user_email,
            'time_range_days': time_range_days
        }

    def _calculate_adaptive_weights(
        self,
        has_survey: bool,
        has_incidents: bool,
        has_github: bool
    ) -> Dict[str, float]:
        """
        Calculate adaptive weights based on available data sources.

        When data is missing, redistribute weights to maintain scoring integrity.
        """
        weights = self.DEFAULT_WEIGHTS.copy()

        if not has_survey and not has_github:
            # Only incident data available
            return {
                'self_reported': 0,
                'incident_load': 100,
                'work_timing': 0
            }

        if not has_survey and has_github:
            # No survey, but have incidents and GitHub
            # Redistribute survey weight proportionally: 35/(35+25) = 58%, 25/(35+25) = 42%
            return {
                'self_reported': 0,
                'incident_load': 58,
                'work_timing': 42
            }

        if has_survey and not has_github:
            # Have survey and incidents, but no GitHub timing data
            # Redistribute timing weight proportionally: 40/(40+35) = 53%, 35/(40+35) = 47%
            return {
                'self_reported': 53,
                'incident_load': 47,
                'work_timing': 0
            }

        # All data available - use default weights
        return weights

    def _calculate_self_reported_score(self, survey_data: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate score from self-reported survey data.

        Survey uses 1-5 scale where:
        - feeling_score: 1 = struggling, 5 = very good
        - workload_score: 1 = overwhelming, 5 = very manageable

        Convert to 0-100 scale where higher = worse:
        - Score 5 (very good) -> 0 (healthy)
        - Score 1 (struggling) -> 100 (critical)
        """
        feeling_score = survey_data.get('feeling_score', 3)  # Default to middle
        workload_score = survey_data.get('workload_score', 3)

        # Convert 1-5 scale to 0-100 scale (inverted: 5->0, 1->100)
        feeling_health = (5 - feeling_score) * 25  # 0-100
        workload_health = (5 - workload_score) * 25  # 0-100

        # Average the two components
        overall_score = (feeling_health + workload_health) / 2

        details = {
            'score': round(overall_score, 1),
            'feeling_score': feeling_score,
            'feeling_health': round(feeling_health, 1),
            'workload_score': workload_score,
            'workload_health': round(workload_health, 1),
            'submitted_at': survey_data.get('submitted_at'),
            'stress_factors': survey_data.get('stress_factors', []),
            'explanation': self._get_survey_explanation(feeling_score, workload_score)
        }

        return overall_score, details

    def _calculate_incident_load_score(
        self,
        incident_data: Dict[str, Any],
        time_range_days: int
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate score from incident load (frequency, severity, response time).

        Components:
        - Incident frequency (40%): incidents per week
        - Severity distribution (40%): weighted by severity
        - After-hours incidents (20%): percentage during off-hours
        """
        total_incidents = incident_data.get('total_incidents', 0)
        severity_dist = incident_data.get('severity_distribution', {})
        after_hours_incidents = incident_data.get('after_hours_incidents', 0)
        avg_response_minutes = incident_data.get('avg_response_minutes', 0)

        # Calculate incidents per week
        incidents_per_week = (total_incidents / time_range_days) * 7

        # Frequency score (0-100, based on incidents/week)
        # 0 incidents/week = 0, 10+ incidents/week = 100
        frequency_score = min(100, (incidents_per_week / 10) * 100)

        # Severity score (0-100, weighted by severity)
        severity_score = self._calculate_severity_score(severity_dist, total_incidents)

        # After-hours percentage score
        after_hours_pct = (after_hours_incidents / total_incidents * 100) if total_incidents > 0 else 0
        # 0% = 0, 50%+ = 100
        after_hours_score = min(100, (after_hours_pct / 50) * 100)

        # Weighted average
        overall_score = (
            frequency_score * 0.4 +
            severity_score * 0.4 +
            after_hours_score * 0.2
        )

        details = {
            'score': round(overall_score, 1),
            'total_incidents': total_incidents,
            'incidents_per_week': round(incidents_per_week, 1),
            'frequency_score': round(frequency_score, 1),
            'severity_score': round(severity_score, 1),
            'severity_distribution': severity_dist,
            'after_hours_incidents': after_hours_incidents,
            'after_hours_percentage': round(after_hours_pct, 1),
            'after_hours_score': round(after_hours_score, 1),
            'avg_response_minutes': round(avg_response_minutes, 1),
            'explanation': self._get_incident_explanation(incidents_per_week, severity_dist, after_hours_pct)
        }

        return overall_score, details

    def _calculate_severity_score(
        self,
        severity_dist: Dict[str, int],
        total_incidents: int
    ) -> float:
        """
        Calculate weighted severity score.

        Severity weights:
        - SEV0/Critical: 5.0x
        - SEV1/High: 3.0x
        - SEV2/Medium: 1.5x
        - SEV3/Low: 0.5x
        - SEV4/Info: 0.2x
        """
        if total_incidents == 0:
            return 0

        severity_weights = {
            'sev0': 5.0,
            'sev1': 3.0,
            'sev2': 1.5,
            'sev3': 0.5,
            'sev4': 0.2,
            'critical': 5.0,
            'high': 3.0,
            'medium': 1.5,
            'low': 0.5,
            'info': 0.2
        }

        weighted_sum = 0
        for severity, count in severity_dist.items():
            weight = severity_weights.get(severity.lower(), 1.0)
            weighted_sum += count * weight

        # Normalize to 0-100 scale
        # Average weight of 2.0 per incident = moderate load
        # Score 100 at 5.0 average weight (all critical incidents)
        avg_weight = weighted_sum / total_incidents if total_incidents > 0 else 0
        score = min(100, (avg_weight / 5.0) * 100)

        return score

    def _calculate_work_timing_score(
        self,
        github_data: Dict[str, Any],
        incident_data: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate score from work timing patterns (GitHub commits + incidents).

        Components:
        - After-hours work (50%): commits/incidents outside 9am-5pm
        - Weekend work (30%): commits/incidents on Sat/Sun
        - Late-night work (20%): commits/incidents 10pm-6am
        """
        total_commits = github_data.get('total_commits', 0)
        after_hours_commits = github_data.get('after_hours_commits', 0)
        weekend_commits = github_data.get('weekend_commits', 0)
        late_night_commits = github_data.get('late_night_commits', 0)

        # Calculate percentages
        after_hours_pct = (after_hours_commits / total_commits * 100) if total_commits > 0 else 0
        weekend_pct = (weekend_commits / total_commits * 100) if total_commits > 0 else 0
        late_night_pct = (late_night_commits / total_commits * 100) if total_commits > 0 else 0

        # Include incident timing if available
        if incident_data:
            total_incidents = incident_data.get('total_incidents', 0)
            after_hours_incidents = incident_data.get('after_hours_incidents', 0)
            weekend_incidents = incident_data.get('weekend_incidents', 0)
            overnight_incidents = incident_data.get('overnight_incidents', 0)

            # Combine commit and incident timing (incidents weighted higher as they're interruptions)
            total_events = total_commits + (total_incidents * 2)  # Weight incidents 2x
            if total_events > 0:
                after_hours_pct = (
                    (after_hours_commits + after_hours_incidents * 2) / total_events * 100
                )
                weekend_pct = (
                    (weekend_commits + weekend_incidents * 2) / total_events * 100
                )
                late_night_pct = (
                    (late_night_commits + overnight_incidents * 2) / total_events * 100
                )

        # Convert percentages to scores (0-100)
        # 0% = 0, 40%+ = 100
        after_hours_score = min(100, (after_hours_pct / 40) * 100)
        weekend_score = min(100, (weekend_pct / 20) * 100)
        late_night_score = min(100, (late_night_pct / 15) * 100)

        # Weighted average
        overall_score = (
            after_hours_score * 0.5 +
            weekend_score * 0.3 +
            late_night_score * 0.2
        )

        details = {
            'score': round(overall_score, 1),
            'after_hours_percentage': round(after_hours_pct, 1),
            'after_hours_score': round(after_hours_score, 1),
            'weekend_percentage': round(weekend_pct, 1),
            'weekend_score': round(weekend_score, 1),
            'late_night_percentage': round(late_night_pct, 1),
            'late_night_score': round(late_night_score, 1),
            'total_commits': total_commits,
            'after_hours_commits': after_hours_commits,
            'weekend_commits': weekend_commits,
            'late_night_commits': late_night_commits,
            'explanation': self._get_timing_explanation(after_hours_pct, weekend_pct, late_night_pct)
        }

        return overall_score, details

    def _calculate_work_timing_from_incidents(
        self,
        incident_data: Dict[str, Any]
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate timing score from incident data only (fallback when no GitHub data).
        """
        total_incidents = incident_data.get('total_incidents', 0)
        after_hours_incidents = incident_data.get('after_hours_incidents', 0)
        weekend_incidents = incident_data.get('weekend_incidents', 0)
        overnight_incidents = incident_data.get('overnight_incidents', 0)

        if total_incidents == 0:
            return 0, {
                'score': 0,
                'after_hours_percentage': 0,
                'weekend_percentage': 0,
                'late_night_percentage': 0,
                'explanation': 'No incidents to analyze timing'
            }

        # Calculate percentages
        after_hours_pct = (after_hours_incidents / total_incidents * 100)
        weekend_pct = (weekend_incidents / total_incidents * 100)
        late_night_pct = (overnight_incidents / total_incidents * 100)

        # Convert to scores
        after_hours_score = min(100, (after_hours_pct / 40) * 100)
        weekend_score = min(100, (weekend_pct / 20) * 100)
        late_night_score = min(100, (late_night_pct / 15) * 100)

        overall_score = (
            after_hours_score * 0.5 +
            weekend_score * 0.3 +
            late_night_score * 0.2
        )

        details = {
            'score': round(overall_score, 1),
            'after_hours_percentage': round(after_hours_pct, 1),
            'weekend_percentage': round(weekend_pct, 1),
            'late_night_percentage': round(late_night_pct, 1),
            'data_source': 'incidents_only',
            'explanation': self._get_timing_explanation(after_hours_pct, weekend_pct, late_night_pct)
        }

        return overall_score, details

    def _get_interpretation(self, score: float) -> str:
        """Get health interpretation from score."""
        for level, (min_score, max_score) in self.SCORE_RANGES.items():
            if min_score <= score < max_score:
                return level
        return 'critical' if score >= 75 else 'healthy'

    def _get_survey_explanation(self, feeling: int, workload: int) -> str:
        """Generate explanation for survey score."""
        feeling_text = {1: 'struggling', 2: 'not great', 3: 'okay', 4: 'good', 5: 'very good'}
        workload_text = {1: 'overwhelming', 2: 'barely manageable', 3: 'somewhat manageable',
                        4: 'manageable', 5: 'very manageable'}
        return f"Feeling: {feeling_text.get(feeling, 'unknown')}, Workload: {workload_text.get(workload, 'unknown')}"

    def _get_incident_explanation(self, per_week: float, severity_dist: Dict, after_hours_pct: float) -> str:
        """Generate explanation for incident load."""
        sev_text = []
        for sev in ['sev0', 'sev1', 'critical', 'high']:
            count = severity_dist.get(sev, 0)
            if count > 0:
                sev_text.append(f"{count} {sev}")

        parts = [f"{per_week:.1f} incidents/week"]
        if sev_text:
            parts.append(f"({', '.join(sev_text)})")
        if after_hours_pct > 30:
            parts.append(f"{after_hours_pct:.0f}% after-hours")

        return ', '.join(parts)

    def _get_timing_explanation(self, after_hours: float, weekend: float, late_night: float) -> str:
        """Generate explanation for work timing."""
        parts = []
        if after_hours > 20:
            parts.append(f"{after_hours:.0f}% after-hours")
        if weekend > 10:
            parts.append(f"{weekend:.0f}% weekend")
        if late_night > 5:
            parts.append(f"{late_night:.0f}% late-night")

        return ', '.join(parts) if parts else 'Mostly during business hours'

    def _generate_transparency_message(
        self,
        has_survey: bool,
        has_incidents: bool,
        has_github: bool,
        weights: Dict[str, float]
    ) -> str:
        """Generate message explaining what data was used."""
        sources = []
        if has_survey:
            sources.append(f"survey data ({weights['self_reported']}%)")
        if has_incidents:
            sources.append(f"incident data ({weights['incident_load']}%)")
        if has_github:
            sources.append(f"GitHub activity ({weights['work_timing']}%)")

        if not sources:
            return "No data available for scoring"

        return f"Score based on: {', '.join(sources)}"


# Global singleton instance
health_scorer = SimpleHealthScorer()
