"""
Copenhagen Burnout Inventory (CBI) Configuration Module

This module implements the Copenhagen Burnout Inventory methodology for burnout assessment.
CBI is scientifically validated and more applicable to software engineers than the Maslach approach.

CBI uses two dimensions for software engineers:
1. Personal Burnout (6 items) - Physical and psychological fatigue/exhaustion
2. Work-Related Burnout (7 items) - Fatigue/exhaustion specifically tied to work

Client-Related Burnout is omitted as it's not applicable to software engineers.
"""

from typing import Dict, Tuple, Any, List
from dataclasses import dataclass
from enum import Enum


class CBIDimension(Enum):
    """CBI Burnout Dimensions"""
    PERSONAL = "personal_burnout"
    WORK_RELATED = "work_related_burnout"


@dataclass
class CBIConfig:
    """Copenhagen Burnout Inventory Configuration"""
    
    # CBI Dimension Weights (must sum to 1.0)
    # Based on CBI research - equal weighting for software engineers
    DIMENSION_WEIGHTS = {
        CBIDimension.PERSONAL: 0.50,        # Physical/psychological fatigue
        CBIDimension.WORK_RELATED: 0.50     # Work-specific fatigue
    }
    
    # Personal Burnout Factor Mappings
    # Maps current metrics to CBI Personal Burnout items (0-100 scale)
    PERSONAL_BURNOUT_FACTORS = {
        'work_hours_trend': {
            'weight': 0.15,  # Reduced to accommodate increased sleep_quality_proxy weight
            'description': 'Physical fatigue from excessive work hours',
            'calculation': 'hours_over_45_per_week',
            'scale_max': 100  # Hours >60/week = 100 burnout
        },
        'weekend_work': {
            'weight': 0.20,
            'description': 'Work-life boundary erosion affecting recovery',
            'calculation': 'weekend_activity_percentage',
            'scale_max': 50  # >50% weekend work = 100 burnout
        },
        'after_hours_activity': {
            'weight': 0.20,
            'description': 'Recovery time interference',
            'calculation': 'after_hours_percentage',
            'scale_max': 40  # >40% after hours = 100 burnout
        },
        'vacation_usage': {
            'weight': 0.15,
            'description': 'Recovery opportunity utilization (inverted)',
            'calculation': 'unused_pto_percentage',
            'scale_max': 80  # 80%+ unused PTO = 100 burnout
        },
        'sleep_quality_proxy': {
            'weight': 0.30,  # Increased weight - SEV1 incidents often happen at night
            'description': 'Energy level estimation from late night activity and incident stress',
            'calculation': 'late_night_commits_frequency_and_incident_stress',
            'scale_max': 20  # >20% commits after 10pm OR high incident stress = 100 burnout
        }
    }
    
    # Work-Related Burnout Factor Mappings
    # Maps current metrics to CBI Work-Related Burnout items (0-100 scale)
    WORK_RELATED_BURNOUT_FACTORS = {
        'sprint_completion': {
            'weight': 0.15,  # Reduced from 0.20
            'description': 'Work pressure from missed deadlines',
            'calculation': 'missed_deadline_percentage',
            'scale_max': 50  # >50% missed deadlines = 100 burnout
        },
        'code_review_speed': {
            'weight': 0.10,  # Reduced from 0.15
            'description': 'Workload sustainability pressure',
            'calculation': 'review_turnaround_stress',
            'scale_max': 120  # >120 hour avg turnaround = 100 burnout
        },
        'pr_frequency': {
            'weight': 0.10,  # Reduced from 0.15
            'description': 'Work intensity from PR volume',
            'calculation': 'pr_volume_stress_score',
            'scale_max': 100  # Excessive or insufficient PRs = stress
        },
        'deployment_frequency': {
            'weight': 0.20,  # Increased back to handle critical incident impact
            'description': 'Delivery pressure from deployment stress',
            'calculation': 'deployment_pressure_score',
            'scale_max': 100  # Failed deploys + high frequency = stress
        },
        'meeting_load': {
            'weight': 0.05,  # Further reduced to accommodate oncall_burden weight increase
            'description': 'Context switching burden',
            'calculation': 'meeting_density_impact',
            'scale_max': 80  # >80% day in meetings = 100 burnout
        },
        'oncall_burden': {
            'weight': 0.40,  # CRITICAL: Dominant weight for incident response stress (Ed's case)
            'description': 'Work-related stress from incident response (severity-weighted)',
            'calculation': 'incident_response_frequency_with_severity',
            'scale_max': 50  # >50 severity-weighted incidents/week = 100 burnout (handles extreme SEV1 loads)
        }
    }
    
    # CBI Score Interpretation Ranges (0-100 scale)
    CBI_SCORE_RANGES = {
        'low': (0, 25),           # Minimal burnout
        'mild': (25, 50),         # Some burnout symptoms
        'moderate': (50, 75),     # Significant burnout
        'high': (75, 100)         # Severe burnout
    }
    
    # Risk Level Mapping (for compatibility with existing system)
    RISK_LEVEL_MAPPING = {
        'low': 'low',           # 0-25 CBI -> low risk
        'mild': 'medium',       # 25-50 CBI -> medium risk  
        'moderate': 'high',     # 50-75 CBI -> high risk
        'high': 'critical'      # 75-100 CBI -> critical risk
    }


def calculate_personal_burnout(metrics: Dict[str, float], config: CBIConfig = None) -> Dict[str, Any]:
    """
    Calculate Personal Burnout score using CBI methodology.
    
    Args:
        metrics: Dict of metric values
        config: Optional config override
        
    Returns:
        Dict with score, components, and details
    """
    if config is None:
        config = CBIConfig()
    
    factors = config.PERSONAL_BURNOUT_FACTORS
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor_name, factor_config in factors.items():
        if factor_name in metrics:
            raw_value = max(0.0, metrics[factor_name])  # Ensure non-negative
            
            # Normalize to 0-100 scale based on factor's scale_max
            normalized_score = min(100.0, (raw_value / factor_config['scale_max']) * 100.0)
            
            # Apply weight
            weighted_score = normalized_score * factor_config['weight']
            component_scores[factor_name] = {
                'raw_value': raw_value,
                'normalized_score': round(normalized_score, 2),
                'weighted_score': round(weighted_score, 2),
                'weight': factor_config['weight'],
                'description': factor_config['description']
            }
            
            weighted_sum += weighted_score
            total_weight += factor_config['weight']
    
    # Calculate final score
    if total_weight > 0:
        final_score = weighted_sum / total_weight
    else:
        final_score = 0.0
    
    return {
        'score': round(final_score, 2),
        'components': component_scores,
        'dimension': CBIDimension.PERSONAL.value,
        'interpretation': get_cbi_interpretation(final_score, config),
        'data_completeness': total_weight
    }


def calculate_work_related_burnout(metrics: Dict[str, float], config: CBIConfig = None) -> Dict[str, Any]:
    """
    Calculate Work-Related Burnout score using CBI methodology.
    
    Args:
        metrics: Dict of metric values
        config: Optional config override
        
    Returns:
        Dict with score, components, and details
    """
    if config is None:
        config = CBIConfig()
    
    factors = config.WORK_RELATED_BURNOUT_FACTORS
    component_scores = {}
    weighted_sum = 0.0
    total_weight = 0.0
    
    for factor_name, factor_config in factors.items():
        if factor_name in metrics:
            raw_value = max(0.0, metrics[factor_name])  # Ensure non-negative
            
            # Normalize to 0-100 scale based on factor's scale_max
            normalized_score = min(100.0, (raw_value / factor_config['scale_max']) * 100.0)
            
            # Apply weight
            weighted_score = normalized_score * factor_config['weight']
            component_scores[factor_name] = {
                'raw_value': raw_value,
                'normalized_score': round(normalized_score, 2),
                'weighted_score': round(weighted_score, 2),
                'weight': factor_config['weight'],
                'description': factor_config['description']
            }
            
            weighted_sum += weighted_score
            total_weight += factor_config['weight']
    
    # Calculate final score
    if total_weight > 0:
        final_score = weighted_sum / total_weight
    else:
        final_score = 0.0
    
    return {
        'score': round(final_score, 2),
        'components': component_scores,
        'dimension': CBIDimension.WORK_RELATED.value,
        'interpretation': get_cbi_interpretation(final_score, config),
        'data_completeness': total_weight
    }


def calculate_composite_cbi_score(personal_score: float, work_related_score: float, 
                                config: CBIConfig = None) -> Dict[str, Any]:
    """
    Calculate composite CBI score from dimension scores.
    
    Args:
        personal_score: Personal Burnout score (0-100)
        work_related_score: Work-Related Burnout score (0-100)
        config: Optional config override
        
    Returns:
        Dict with composite score and analysis
    """
    if config is None:
        config = CBIConfig()
    
    weights = config.DIMENSION_WEIGHTS
    
    # Calculate weighted average
    composite_score = (
        personal_score * weights[CBIDimension.PERSONAL] +
        work_related_score * weights[CBIDimension.WORK_RELATED]
    )
    
    interpretation = get_cbi_interpretation(composite_score, config)
    risk_level = config.RISK_LEVEL_MAPPING[interpretation]
    
    return {
        'composite_score': round(composite_score, 2),
        'personal_score': round(personal_score, 2),
        'work_related_score': round(work_related_score, 2),
        'interpretation': interpretation,
        'risk_level': risk_level,
        'dimension_weights': dict(weights),
        'score_breakdown': {
            'personal_contribution': round(personal_score * weights[CBIDimension.PERSONAL], 2),
            'work_related_contribution': round(work_related_score * weights[CBIDimension.WORK_RELATED], 2)
        }
    }


def get_cbi_interpretation(score: float, config: CBIConfig = None) -> str:
    """
    Get CBI score interpretation based on standard ranges.
    
    Args:
        score: CBI score (0-100)
        config: Optional config override
        
    Returns:
        Interpretation string: 'low', 'mild', 'moderate', or 'high'
    """
    if config is None:
        config = CBIConfig()
    
    ranges = config.CBI_SCORE_RANGES
    
    for level, (min_score, max_score) in ranges.items():
        if min_score <= score < max_score:
            return level
    
    # Handle edge case for score = 100
    if score >= 75:
        return 'high'
    
    return 'low'


def validate_cbi_config(config: CBIConfig = None) -> Dict[str, bool]:
    """
    Validate CBI configuration for mathematical consistency.
    
    Args:
        config: Config to validate
        
    Returns:
        Dict of validation results
    """
    if config is None:
        config = CBIConfig()
    
    results = {}
    
    # Check dimension weights sum to 1.0
    dimension_sum = sum(config.DIMENSION_WEIGHTS.values())
    results['dimension_weights_sum'] = abs(dimension_sum - 1.0) < 0.001
    
    # Check personal burnout factor weights sum to 1.0
    personal_sum = sum(factor['weight'] for factor in config.PERSONAL_BURNOUT_FACTORS.values())
    results['personal_factors_sum'] = abs(personal_sum - 1.0) < 0.001
    
    # Check work-related burnout factor weights sum to 1.0
    work_sum = sum(factor['weight'] for factor in config.WORK_RELATED_BURNOUT_FACTORS.values())
    results['work_related_factors_sum'] = abs(work_sum - 1.0) < 0.001
    
    # Check score ranges are properly ordered and cover 0-100
    ranges = config.CBI_SCORE_RANGES
    results['score_ranges_valid'] = (
        ranges['low'][0] == 0 and
        ranges['low'][1] == ranges['mild'][0] and
        ranges['mild'][1] == ranges['moderate'][0] and
        ranges['moderate'][1] == ranges['high'][0] and
        ranges['high'][1] == 100
    )
    
    # Check all scale_max values are positive
    personal_scales_valid = all(
        factor['scale_max'] > 0 
        for factor in config.PERSONAL_BURNOUT_FACTORS.values()
    )
    work_scales_valid = all(
        factor['scale_max'] > 0 
        for factor in config.WORK_RELATED_BURNOUT_FACTORS.values()
    )
    results['scale_max_positive'] = personal_scales_valid and work_scales_valid
    
    return results


def generate_cbi_score_reasoning(
    personal_result: Dict[str, Any], 
    work_result: Dict[str, Any], 
    composite_result: Dict[str, Any],
    raw_metrics: Dict[str, Any] = None
) -> List[str]:
    """
    Generate human-readable explanations for why someone has their CBI score.
    
    Args:
        personal_result: Personal burnout calculation result
        work_result: Work-related burnout calculation result
        composite_result: Composite CBI score result
        raw_metrics: Original metrics data for context
        
    Returns:
        List of reasoning strings explaining the score
    """
    reasons = []
    personal_score = personal_result['score']
    work_score = work_result['score']
    composite_score = composite_result['composite_score']
    
    # Overall score context
    if composite_score >= 75:
        reasons.append(f"Critical burnout risk (CBI: {composite_score:.0f}/100) - immediate attention needed")
    elif composite_score >= 50:
        reasons.append(f"High burnout risk (CBI: {composite_score:.0f}/100) - monitor closely")
    elif composite_score >= 25:
        reasons.append(f"Moderate stress levels (CBI: {composite_score:.0f}/100) - manageable with care")
    else:
        reasons.append(f"Low burnout risk (CBI: {composite_score:.0f}/100) - healthy stress levels")
    
    # Personal burnout contributors
    if personal_score > 50:
        personal_components = personal_result.get('components', {})
        top_personal = sorted(personal_components.items(), key=lambda x: x[1].get('weighted_score', 0), reverse=True)
        
        reasons.append("Personal burnout factors:")
        for factor_name, factor_data in top_personal[:3]:  # Top 3 contributors
            weighted_score = factor_data.get('weighted_score', 0)
            if weighted_score > 5:  # Only show significant contributors
                if factor_name == 'work_hours_trend':
                    reasons.append(f"   • Excessive work hours contributing {weighted_score:.1f} points")
                elif factor_name == 'weekend_work':
                    reasons.append(f"   • Weekend incident work adding {weighted_score:.1f} points of stress")
                elif factor_name == 'after_hours_activity':
                    reasons.append(f"   • After-hours incidents disrupting work-life balance ({weighted_score:.1f} points)")
                elif factor_name == 'vacation_usage':
                    reasons.append(f"   • High incident load preventing proper recovery time ({weighted_score:.1f} points)")
                elif factor_name == 'sleep_quality_proxy':
                    reasons.append(f"   • Critical incidents and on-call stress affecting sleep quality ({weighted_score:.1f} points)")
    
    # Work-related burnout contributors  
    if work_score > 50:
        work_components = work_result.get('components', {})
        top_work = sorted(work_components.items(), key=lambda x: x[1].get('weighted_score', 0), reverse=True)
        
        reasons.append("Work-related burnout factors:")
        for factor_name, factor_data in top_work[:3]:  # Top 3 contributors
            weighted_score = factor_data.get('weighted_score', 0)
            if weighted_score > 5:  # Only show significant contributors
                if factor_name == 'sprint_completion':
                    reasons.append(f"   • High-pressure response times creating stress ({weighted_score:.1f} points)")
                elif factor_name == 'pr_frequency':
                    reasons.append(f"   • Heavy severity-weighted incident workload ({weighted_score:.1f} points)")
                elif factor_name == 'deployment_frequency':
                    reasons.append(f"   • Critical production incidents adding deployment pressure ({weighted_score:.1f} points)")
                elif factor_name == 'meeting_load':
                    reasons.append(f"   • Incident response meetings and postmortem overhead ({weighted_score:.1f} points)")
                elif factor_name == 'oncall_burden':
                    reasons.append(f"   • Severity-weighted on-call burden with baseline stress ({weighted_score:.1f} points)")
    
    # Specific severity insights
    if raw_metrics:
        severity_dist = raw_metrics.get('severity_distribution', {})
        sev0_count = severity_dist.get('sev0', 0)
        sev1_count = severity_dist.get('sev1', 0)
        
        if sev0_count > 0:
            reasons.append(f"Handled {sev0_count} critical SEV0 incident{'s' if sev0_count != 1 else ''} (5x burnout impact)")
        if sev1_count > 0:
            reasons.append(f"Managed {sev1_count} high-impact SEV1 incident{'s' if sev1_count != 1 else ''} (4x burnout impact)")
        
        total_incidents = sum(severity_dist.values()) if severity_dist else 0
        if total_incidents > 0:
            reasons.append(f"On-call baseline stress from handling {total_incidents} total incidents")
    
    # Dimensional comparison
    if abs(personal_score - work_score) > 15:
        if personal_score > work_score:
            reasons.append("Personal stress significantly higher than work stress - focus on recovery and boundaries")
        else:
            reasons.append("Work stress significantly higher than personal stress - address workload and processes")
    
    return reasons


def get_cbi_recommendations(cbi_result: Dict[str, Any]) -> List[str]:
    """
    Generate actionable recommendations based on CBI scores.
    
    Args:
        cbi_result: Result from calculate_composite_cbi_score
        
    Returns:
        List of recommendation strings
    """
    recommendations = []
    composite_score = cbi_result['composite_score']
    personal_score = cbi_result['personal_score']
    work_related_score = cbi_result['work_related_score']
    
    # General recommendations based on composite score
    if composite_score >= 75:
        recommendations.append("Consider taking time off or reducing workload immediately")
        recommendations.append("Schedule a meeting with your manager about workload concerns")
    elif composite_score >= 50:
        recommendations.append("Monitor workload and stress levels closely")
        recommendations.append("Consider stress management techniques or counseling")
    elif composite_score >= 25:
        recommendations.append("Practice good work-life balance habits")
        recommendations.append("Regular exercise and adequate sleep are important")
    else:
        recommendations.append("Maintain current work-life balance habits")
        recommendations.append("Continue regular exercise and adequate sleep routines")
    
    # Specific recommendations based on dimension scores
    if personal_score > work_related_score + 15:
        recommendations.append("Focus on personal recovery: sleep, exercise, and downtime")
        recommendations.append("Consider if work hours are sustainable long-term")
    elif work_related_score > personal_score + 15:
        recommendations.append("Address work-specific stressors: deadlines, workload, or team dynamics")
        recommendations.append("Discuss work processes and expectations with your team")
    
    return recommendations


# Global singleton instance
DEFAULT_CBI_CONFIG = CBIConfig()