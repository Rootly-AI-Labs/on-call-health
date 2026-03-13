"""
Alert Health Score Calculator

Calculates a normalized alert health score (0-100) that measures alert burden and quality.
Used as a factor in OCH (On-Call Health) work-related burnout dimension.

The score combines alert metrics with research-informed weights to measure on-call stress:
- Level 1 (Highest Impact): Night-time alerts, Escalation rate, Retriggered rate
- Level 2 (Medium Impact): Alerts with incidents, After-hours alerts, Signal quality
"""

from typing import Dict, Any, Optional


def calculate_alert_health_score(
    total_alerts: int,
    night_time_alerts: int = 0,
    escalated_alerts: int = 0,
    retriggered_alerts: int = 0,
    alerts_with_incidents: int = 0,
    after_hours_alerts: int = 0,
    signal_quality_pct: float = 100.0
) -> Dict[str, Any]:
    """
    Calculate normalized alert health score (0-100).

    Works for both team-level and individual user-level alerts.
    All metrics are ratios/percentages, so naturally normalized across different volumes.

    Args:
        total_alerts: Total number of alerts in period
        night_time_alerts: Alerts between 10pm-6am (sleep disruption)
        escalated_alerts: Alerts escalated (can't resolve independently)
        retriggered_alerts: Alerts that retriggered (fix didn't stick)
        alerts_with_incidents: Alerts converted to incidents (business impact)
        after_hours_alerts: Alerts outside business hours (work-life balance)
        signal_quality_pct: % of non-noise alerts (100 = all actionable)

    Returns:
        Dict with:
            - score: Normalized 0-100 alert health score
            - components: Breakdown of each metric contribution
            - interpretation: Risk level interpretation
    """

    # Sanitize inputs: clamp to non-negative and ensure sub-counts don't exceed total
    total_alerts = max(0, int(total_alerts))
    night_time_alerts = max(0, min(int(night_time_alerts), total_alerts))
    escalated_alerts = max(0, min(int(escalated_alerts), total_alerts))
    retriggered_alerts = max(0, min(int(retriggered_alerts), total_alerts))
    alerts_with_incidents = max(0, min(int(alerts_with_incidents), total_alerts))
    after_hours_alerts = max(0, min(int(after_hours_alerts), total_alerts))
    signal_quality_pct = max(0.0, min(float(signal_quality_pct), 100.0))

    # Avoid division by zero
    if total_alerts == 0:
        return {
            'score': 0.0,
            'components': {
                'night_time_pct': 0.0,
                'escalation_rate': 0.0,
                'retriggered_rate': 0.0,
                'with_incidents_pct': 0.0,
                'after_hours_pct': 0.0,
                'signal_quality_noise': 0.0
            },
            'interpretation': 'low',
            'reasoning': 'No alerts in period'
        }

    # Calculate each metric as a percentage/ratio (all 0-100 after clamping above)
    night_time_pct = (night_time_alerts / total_alerts) * 100
    escalation_rate = (escalated_alerts / total_alerts) * 100
    retriggered_rate = (retriggered_alerts / total_alerts) * 100
    with_incidents_pct = (alerts_with_incidents / total_alerts) * 100
    after_hours_pct = (after_hours_alerts / total_alerts) * 100
    signal_quality_noise = 100 - signal_quality_pct  # Inverted: higher noise = worse

    # Apply research-informed weights (Level 1 = 45%, Level 2 = 30%)
    alert_health_raw = (
        (night_time_pct * 0.15) +              # Level 1 - Direct sleep impact
        (escalation_rate * 0.15) +             # Level 1 - Can't resolve independently
        (retriggered_rate * 0.15) +            # Level 1 - Fixes not sticking = rework
        (with_incidents_pct * 0.10) +          # Level 2 - Real business impact
        (after_hours_pct * 0.10) +             # Level 2 - Work-life balance violation
        (signal_quality_noise * 0.05)          # Level 2 - Alert fatigue from noise
    ) / 100

    # Normalize to 0-100 scale and cap at 100
    alert_health_score = min(100.0, alert_health_raw * 100)

    # Interpret the score
    interpretation = _interpret_alert_health(alert_health_score)

    # Calculate component contributions
    components = {
        'night_time_pct': night_time_pct,
        'escalation_rate': escalation_rate,
        'retriggered_rate': retriggered_rate,
        'with_incidents_pct': with_incidents_pct,
        'after_hours_pct': after_hours_pct,
        'signal_quality_noise': signal_quality_noise
    }

    return {
        'score': round(alert_health_score, 2),
        'components': {k: round(v, 2) for k, v in components.items()},
        'interpretation': interpretation,
        'weighted_contributions': {
            'night_time': round(night_time_pct * 0.15, 2),
            'escalation': round(escalation_rate * 0.15, 2),
            'retriggered': round(retriggered_rate * 0.15, 2),
            'with_incidents': round(with_incidents_pct * 0.10, 2),
            'after_hours': round(after_hours_pct * 0.10, 2),
            'noise': round(signal_quality_noise * 0.05, 2)
        },
        'raw_metrics': {
            'total_alerts': total_alerts,
            'night_time_alerts': night_time_alerts,
            'escalated_alerts': escalated_alerts,
            'retriggered_alerts': retriggered_alerts,
            'alerts_with_incidents': alerts_with_incidents,
            'after_hours_alerts': after_hours_alerts,
            'signal_quality_pct': round(signal_quality_pct, 2)
        }
    }


def _interpret_alert_health(score: float) -> str:
    """
    Interpret alert health score into risk level.

    Args:
        score: Alert health score (0-100)

    Returns:
        Interpretation: 'low', 'mild', 'moderate', or 'high'
    """
    if score < 25:
        return 'low'
    elif score < 50:
        return 'mild'
    elif score < 75:
        return 'moderate'
    else:
        return 'high'


def get_alert_health_reasoning(alert_health_result: Dict[str, Any]) -> str:
    """
    Generate human-readable explanation of alert health score.

    Args:
        alert_health_result: Result dict from calculate_alert_health_score()

    Returns:
        String explanation of the score and contributing factors
    """
    score = alert_health_result['score']
    interpretation = alert_health_result['interpretation']
    components = alert_health_result['components']

    # Overall score message
    if score >= 75:
        overall = "Critical alert burden - immediate action needed"
    elif score >= 50:
        overall = "High alert burden - monitor and improve"
    elif score >= 25:
        overall = "Moderate alert burden - manageable with attention"
    else:
        overall = "Healthy alert metrics"

    # Find top contributing factors
    contributions = alert_health_result['weighted_contributions']
    top_factors = sorted(contributions.items(), key=lambda x: x[1], reverse=True)[:3]

    factors_text = "Top contributors:"
    for factor_name, contribution in top_factors:
        if contribution > 0:
            readable_name = {
                'night_time': 'Night-time alerts (sleep disruption)',
                'escalation': 'Escalations (can\'t resolve)',
                'retriggered': 'Retriggered alerts (fixes not sticking)',
                'with_incidents': 'Alerts with incidents (business impact)',
                'after_hours': 'After-hours alerts (work-life balance)',
                'noise': 'Alert noise/fatigue'
            }.get(factor_name, factor_name)
            factors_text += f" {readable_name} ({contribution:.1f})"

    return f"{overall} (Score: {score:.0f}/100). {factors_text}"
