"""
Unified Platform Integration Scoring Framework

This module provides standardized scoring for platform integrations (Rootly, PagerDuty)
to ensure consistent evaluation across different data sources and integration quality.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ScoreLevel(Enum):
    """Standardized score levels across all platforms."""
    EXCELLENT = "excellent"  # 90-100%
    GOOD = "good"           # 70-89%
    FAIR = "fair"           # 50-69%
    POOR = "poor"           # 30-49%
    CRITICAL = "critical"   # 0-29%

class PlatformType(Enum):
    """Supported platform types."""
    ROOTLY = "rootly"
    PAGERDUTY = "pagerduty"
    GITHUB = "github"
    SLACK = "slack"

@dataclass
class PlatformScore:
    """Standardized platform scoring result."""
    overall_score: float  # 0-1 scale
    level: ScoreLevel
    percentage: int       # 0-100 for display
    components: Dict[str, float]  # Individual component scores
    recommendations: List[Dict[str, str]]
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "overall_score": round(self.overall_score, 3),
            "level": self.level.value,
            "percentage": self.percentage,
            "components": {k: round(v, 3) for k, v in self.components.items()},
            "recommendations": self.recommendations,
            "metadata": self.metadata or {}
        }

class PlatformScoringFramework:
    """Main framework for calculating platform integration scores."""
    
    # Score thresholds (0-1 scale)
    THRESHOLDS = {
        ScoreLevel.EXCELLENT: (0.90, 1.0),
        ScoreLevel.GOOD: (0.70, 0.89),
        ScoreLevel.FAIR: (0.50, 0.69),
        ScoreLevel.POOR: (0.30, 0.49),
        ScoreLevel.CRITICAL: (0.0, 0.29)
    }
    
    # Component weights by platform
    COMPONENT_WEIGHTS = {
        PlatformType.ROOTLY: {
            "token_validity": 0.25,      # Is token working?
            "permission_coverage": 0.30, # Does token have required permissions?
            "data_availability": 0.25,   # Is data accessible?
            "data_quality": 0.20         # Is data complete and recent?
        },
        PlatformType.PAGERDUTY: {
            "token_validity": 0.25,
            "permission_coverage": 0.30,
            "data_availability": 0.25,
            "data_quality": 0.20
        },
        PlatformType.GITHUB: {
            "token_validity": 0.20,
            "org_access": 0.30,          # Can access required organizations
            "member_coverage": 0.25,     # Can fetch member profiles
            "mapping_success": 0.25      # Success rate of user matching
        },
        PlatformType.SLACK: {
            "token_validity": 0.25,
            "workspace_access": 0.30,
            "channel_coverage": 0.25,
            "message_access": 0.20
        }
    }
    
    @classmethod
    def calculate_platform_score(
        cls,
        platform_type: PlatformType,
        components: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> PlatformScore:
        """
        Calculate overall platform score from component scores.
        
        Args:
            platform_type: Type of platform being scored
            components: Dictionary of component names to scores (0-1 scale)
            metadata: Optional additional data for context
            
        Returns:
            PlatformScore object with overall score and recommendations
        """
        weights = cls.COMPONENT_WEIGHTS.get(platform_type)
        if not weights:
            raise ValueError(f"Unsupported platform type: {platform_type}")
        
        # Calculate weighted average
        total_score = 0.0
        total_weight = 0.0
        
        for component, weight in weights.items():
            if component in components:
                component_score = max(0.0, min(1.0, components[component]))  # Clamp to 0-1
                total_score += component_score * weight
                total_weight += weight
        
        # Handle missing components by treating them as 0
        if total_weight < 1.0:
            logger.warning(f"Missing components for {platform_type.value}: {set(weights.keys()) - set(components.keys())}")
        
        overall_score = total_score / max(total_weight, 1.0) if total_weight > 0 else 0.0
        
        # Determine score level
        level = cls._determine_score_level(overall_score)
        percentage = int(overall_score * 100)
        
        # Generate recommendations
        recommendations = cls._generate_recommendations(platform_type, components, level, metadata)
        
        return PlatformScore(
            overall_score=overall_score,
            level=level,
            percentage=percentage,
            components=components,
            recommendations=recommendations,
            metadata=metadata
        )
    
    @classmethod
    def _determine_score_level(cls, score: float) -> ScoreLevel:
        """Determine score level from numeric score."""
        for level, (min_score, max_score) in cls.THRESHOLDS.items():
            if min_score <= score <= max_score:
                return level
        return ScoreLevel.CRITICAL  # Fallback
    
    @classmethod
    def _generate_recommendations(
        cls,
        platform_type: PlatformType,
        components: Dict[str, float],
        level: ScoreLevel,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on scores."""
        recommendations = []
        
        # Generic low component score recommendations
        for component, score in components.items():
            if score < 0.5:  # Poor performance
                rec = cls._get_component_recommendation(platform_type, component, score, metadata)
                if rec:
                    recommendations.append(rec)
        
        # Overall level recommendations
        if level == ScoreLevel.CRITICAL:
            recommendations.append({
                "type": "error",
                "title": "Critical Integration Issues",
                "message": f"{platform_type.value.title()} integration has critical issues that prevent proper data collection.",
                "action": "Review and fix token permissions or connectivity issues."
            })
        elif level == ScoreLevel.POOR:
            recommendations.append({
                "type": "warning", 
                "title": "Poor Integration Health",
                "message": f"{platform_type.value.title()} integration needs attention to improve data quality.",
                "action": "Check component scores and address failing areas."
            })
        elif level == ScoreLevel.EXCELLENT:
            recommendations.append({
                "type": "success",
                "title": "Integration Working Perfectly",
                "message": f"{platform_type.value.title()} integration is performing excellently.",
                "action": "No action needed - continue monitoring."
            })
        
        return recommendations
    
    @classmethod
    def _get_component_recommendation(
        cls,
        platform_type: PlatformType,
        component: str,
        score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, str]]:
        """Get specific recommendation for a failing component."""
        
        # Platform-specific component recommendations
        if platform_type == PlatformType.ROOTLY:
            if component == "token_validity" and score < 0.5:
                return {
                    "type": "error",
                    "title": "Invalid Rootly Token",
                    "message": "Your Rootly API token is invalid or expired.",
                    "action": "Generate a new API token from your Rootly account settings."
                }
            elif component == "permission_coverage" and score < 0.5:
                return {
                    "type": "error",
                    "title": "Missing Rootly Permissions",
                    "message": "Your API token lacks required permissions for incidents or users.",
                    "action": "Update token permissions to include 'incidents:read' and 'users:read'."
                }
            elif component == "data_availability" and score < 0.5:
                return {
                    "type": "warning",
                    "title": "Limited Rootly Data",
                    "message": "Unable to fetch sufficient incident or user data.",
                    "action": "Check if your organization has recent incidents and active users."
                }
            elif component == "data_quality" and score < 0.5:
                return {
                    "type": "warning",
                    "title": "Poor Rootly Data Quality",
                    "message": "Incident or user data is incomplete or outdated.",
                    "action": "Verify data completeness in your Rootly account."
                }
        
        elif platform_type == PlatformType.PAGERDUTY:
            if component == "token_validity" and score < 0.5:
                return {
                    "type": "error",
                    "title": "Invalid PagerDuty Token",
                    "message": "Your PagerDuty API token is invalid or expired.",
                    "action": "Generate a new API token from your PagerDuty account."
                }
            elif component == "permission_coverage" and score < 0.5:
                return {
                    "type": "error",
                    "title": "Missing PagerDuty Permissions",
                    "message": "Your API token lacks required permissions for incidents or users.",
                    "action": "Update token permissions to include incident and user read access."
                }
        
        elif platform_type == PlatformType.GITHUB:
            if component == "token_validity" and score < 0.5:
                return {
                    "type": "error",
                    "title": "Invalid GitHub Token",
                    "message": "Your GitHub personal access token is invalid or expired.",
                    "action": "Generate a new personal access token with required scopes."
                }
            elif component == "org_access" and score < 0.5:
                return {
                    "type": "error",
                    "title": "GitHub Organization Access",
                    "message": "Cannot access required GitHub organizations.",
                    "action": "Ensure your token has access to your team's organizations."
                }
            elif component == "mapping_success" and score < 0.5:
                return {
                    "type": "warning",
                    "title": "Low GitHub Mapping Success",
                    "message": "Unable to match many team members to GitHub accounts.",
                    "action": "Review team member names and GitHub profiles for matching."
                }
        
        return None

# Convenience functions for common scoring scenarios

def score_rootly_integration(
    token_valid: bool,
    permissions: Dict[str, bool],
    users_count: int,
    incidents_count: int,
    data_days: int = 7,
    metadata: Optional[Dict[str, Any]] = None
) -> PlatformScore:
    """
    Score Rootly integration health.
    
    Args:
        token_valid: Whether token authentication succeeded
        permissions: Dict of permission name to access status
        users_count: Number of users fetched
        incidents_count: Number of incidents fetched
        data_days: Days of data attempted to fetch
        metadata: Additional context data
    """
    components = {
        "token_validity": 1.0 if token_valid else 0.0,
        "permission_coverage": _calculate_permission_score(permissions, ["users", "incidents"]),
        "data_availability": _calculate_data_availability_score(users_count, incidents_count),
        "data_quality": _calculate_data_quality_score(incidents_count, data_days)
    }
    
    return PlatformScoringFramework.calculate_platform_score(
        PlatformType.ROOTLY, 
        components, 
        metadata
    )

def score_pagerduty_integration(
    token_valid: bool,
    permissions: Dict[str, bool], 
    users_count: int,
    incidents_count: int,
    services_count: int = 0,
    data_days: int = 7,
    metadata: Optional[Dict[str, Any]] = None
) -> PlatformScore:
    """Score PagerDuty integration health."""
    components = {
        "token_validity": 1.0 if token_valid else 0.0,
        "permission_coverage": _calculate_permission_score(permissions, ["users", "incidents", "services"]),
        "data_availability": _calculate_data_availability_score(users_count, incidents_count + services_count),
        "data_quality": _calculate_data_quality_score(incidents_count, data_days)
    }
    
    return PlatformScoringFramework.calculate_platform_score(
        PlatformType.PAGERDUTY,
        components,
        metadata
    )

def score_github_integration(
    token_valid: bool,
    orgs_accessible: int,
    total_members: int,
    profiles_loaded: int,
    mapping_success_rate: float,
    metadata: Optional[Dict[str, Any]] = None
) -> PlatformScore:
    """Score GitHub integration health."""
    components = {
        "token_validity": 1.0 if token_valid else 0.0,
        "org_access": min(1.0, orgs_accessible / max(1, 2)),  # Expect at least 2 orgs
        "member_coverage": profiles_loaded / max(total_members, 1) if total_members > 0 else 0.0,
        "mapping_success": mapping_success_rate  # Already 0-1 scale
    }
    
    return PlatformScoringFramework.calculate_platform_score(
        PlatformType.GITHUB,
        components,
        metadata
    )

# Helper functions

def _calculate_permission_score(permissions: Dict[str, bool], required_permissions: List[str]) -> float:
    """Calculate score based on required permissions availability."""
    if not required_permissions:
        return 1.0
    
    granted_count = sum(1 for perm in required_permissions if permissions.get(perm, False))
    return granted_count / len(required_permissions)

def _calculate_data_availability_score(users_count: int, data_count: int) -> float:
    """Score based on whether we can fetch basic data."""
    # Score based on having users and some data
    user_score = min(1.0, users_count / 5)  # Expect at least 5 users for full score
    data_score = 1.0 if data_count > 0 else 0.0  # Any data is good
    
    return (user_score * 0.6) + (data_score * 0.4)

def _calculate_data_quality_score(data_count: int, data_days: int) -> float:
    """Score based on data recency and volume."""
    # More recent data and higher volume = better quality
    volume_score = min(1.0, data_count / 10)  # Expect at least 10 data points for full score
    recency_score = min(1.0, data_days / 7)   # 7+ days of data for full score
    
    return (volume_score * 0.7) + (recency_score * 0.3)

# Export main components
__all__ = [
    "PlatformScore",
    "ScoreLevel", 
    "PlatformType",
    "PlatformScoringFramework",
    "score_rootly_integration",
    "score_pagerduty_integration", 
    "score_github_integration"
]