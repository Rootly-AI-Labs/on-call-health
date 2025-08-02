"""
Burnout Prediction Tool for Burnout Detection Agent

Uses historical patterns and current trends to predict future burnout risk:
- Trend analysis on key metrics
- Early warning signal detection
- Risk trajectory prediction
- Intervention timing recommendations
"""
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import statistics
import math
import logging

logger = logging.getLogger(__name__)


class BurnoutPredictorTool:
    """Tool for predicting future burnout risk based on trends and patterns."""
    
    def __init__(self):
        self.name = "burnout_predictor"
        self.description = "Predicts future burnout risk using trend analysis and pattern recognition"
        
    def __call__(
        self, 
        historical_analyses: List[Dict[str, Any]],
        current_metrics: Dict[str, Any],
        time_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Predict future burnout risk based on historical data and current trends.
        
        Args:
            historical_analyses: List of past burnout analyses (ordered by date)
            current_metrics: Current burnout metrics and indicators
            time_horizon_days: Prediction time horizon in days
            
        Returns:
            Dictionary with predictions, early warnings, and recommendations
        """
        predictions = {
            "predicted_risk_level": "unknown",
            "risk_trajectory": "stable",
            "confidence_score": 0.0,
            "early_warning_signals": [],
            "critical_thresholds": {},
            "intervention_recommendations": [],
            "trend_analysis": {},
            "predicted_timeline": {}
        }
        
        if not historical_analyses:
            predictions["early_warning_signals"].append("Insufficient historical data for prediction")
            return predictions
        
        # Analyze trends in key metrics
        predictions["trend_analysis"] = self._analyze_metric_trends(historical_analyses, current_metrics)
        
        # Detect early warning signals
        predictions["early_warning_signals"] = self._detect_early_warnings(
            predictions["trend_analysis"], current_metrics
        )
        
        # Calculate critical thresholds
        predictions["critical_thresholds"] = self._calculate_critical_thresholds(
            historical_analyses, current_metrics
        )
        
        # Predict risk trajectory
        trajectory_data = self._predict_risk_trajectory(
            predictions["trend_analysis"], 
            current_metrics, 
            time_horizon_days
        )
        predictions.update(trajectory_data)
        
        # Generate timeline predictions
        predictions["predicted_timeline"] = self._generate_timeline_predictions(
            predictions["trend_analysis"],
            current_metrics,
            time_horizon_days
        )
        
        # Generate intervention recommendations
        predictions["intervention_recommendations"] = self._generate_intervention_recommendations(
            predictions
        )
        
        logger.info(f"Burnout prediction - Risk: {predictions['predicted_risk_level']}, Trajectory: {predictions['risk_trajectory']}, Warnings: {len(predictions['early_warning_signals'])}")
        
        return predictions
    
    def _analyze_metric_trends(
        self, 
        historical_analyses: List[Dict], 
        current_metrics: Dict
    ) -> Dict[str, Any]:
        """Analyze trends in key burnout metrics."""
        trends = {
            "burnout_score_trend": {},
            "incident_load_trend": {},
            "after_hours_trend": {},
            "weekend_work_trend": {},
            "response_time_trend": {},
            "sentiment_trend": {}
        }
        
        # Extract time series data
        burnout_scores = []
        incident_counts = []
        after_hours_percentages = []
        weekend_percentages = []
        response_times = []
        sentiment_scores = []
        
        for analysis in historical_analyses[-10:]:  # Last 10 analyses
            if "burnout_score" in analysis:
                burnout_scores.append(analysis["burnout_score"])
            if "incident_count" in analysis:
                incident_counts.append(analysis["incident_count"])
            if "after_hours_percentage" in analysis:
                after_hours_percentages.append(analysis["after_hours_percentage"])
            if "weekend_percentage" in analysis:
                weekend_percentages.append(analysis["weekend_percentage"])
            if "avg_response_time" in analysis:
                response_times.append(analysis["avg_response_time"])
            if "sentiment_score" in analysis:
                sentiment_scores.append(analysis["sentiment_score"])
        
        # Add current metrics
        if "burnout_score" in current_metrics:
            burnout_scores.append(current_metrics["burnout_score"])
        if "incident_count" in current_metrics:
            incident_counts.append(current_metrics["incident_count"])
        if "after_hours_percentage" in current_metrics:
            after_hours_percentages.append(current_metrics["after_hours_percentage"])
        if "weekend_percentage" in current_metrics:
            weekend_percentages.append(current_metrics["weekend_percentage"])
        if "avg_response_time" in current_metrics:
            response_times.append(current_metrics["avg_response_time"])
        if "sentiment_score" in current_metrics:
            sentiment_scores.append(current_metrics["sentiment_score"])
        
        # Calculate trends for each metric
        trends["burnout_score_trend"] = self._calculate_trend(burnout_scores, "burnout_score")
        trends["incident_load_trend"] = self._calculate_trend(incident_counts, "incident_load")
        trends["after_hours_trend"] = self._calculate_trend(after_hours_percentages, "after_hours")
        trends["weekend_work_trend"] = self._calculate_trend(weekend_percentages, "weekend_work")
        trends["response_time_trend"] = self._calculate_trend(response_times, "response_time")
        trends["sentiment_trend"] = self._calculate_trend(sentiment_scores, "sentiment", inverse=True)
        
        return trends
    
    def _calculate_trend(
        self, 
        values: List[float], 
        metric_name: str,
        inverse: bool = False
    ) -> Dict[str, Any]:
        """Calculate trend statistics for a metric."""
        if len(values) < 2:
            return {
                "direction": "insufficient_data",
                "slope": 0,
                "acceleration": 0,
                "volatility": 0
            }
        
        # Calculate linear regression slope
        x_values = list(range(len(values)))
        mean_x = statistics.mean(x_values)
        mean_y = statistics.mean(values)
        
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, values))
        denominator = sum((x - mean_x) ** 2 for x in x_values)
        
        slope = numerator / denominator if denominator != 0 else 0
        
        # Adjust for inverse metrics (where lower is worse, like sentiment)
        if inverse:
            slope = -slope
        
        # Calculate acceleration (change in slope)
        acceleration = 0
        if len(values) >= 4:
            mid_point = len(values) // 2
            first_half_slope = self._calculate_simple_slope(values[:mid_point])
            second_half_slope = self._calculate_simple_slope(values[mid_point:])
            acceleration = second_half_slope - first_half_slope
        
        # Calculate volatility
        volatility = statistics.stdev(values) / statistics.mean(values) if len(values) > 1 and statistics.mean(values) != 0 else 0
        
        # Determine direction
        if slope > 0.1:
            direction = "increasing"
        elif slope < -0.1:
            direction = "decreasing"
        else:
            direction = "stable"
        
        # Check for concerning patterns
        if acceleration > 0.2 and slope > 0:
            direction = "accelerating_increase"
        elif acceleration < -0.2 and slope < 0:
            direction = "accelerating_decrease"
        
        return {
            "direction": direction,
            "slope": round(slope, 3),
            "acceleration": round(acceleration, 3),
            "volatility": round(volatility, 3),
            "current_value": values[-1] if values else 0,
            "mean_value": round(statistics.mean(values), 2) if values else 0,
            "data_points": len(values)
        }
    
    def _calculate_simple_slope(self, values: List[float]) -> float:
        """Calculate simple slope for a subset of values."""
        if len(values) < 2:
            return 0
        return (values[-1] - values[0]) / (len(values) - 1)
    
    def _detect_early_warnings(
        self, 
        trend_analysis: Dict[str, Any], 
        current_metrics: Dict[str, Any]
    ) -> List[str]:
        """Detect early warning signals of impending burnout."""
        warnings = []
        
        # Check burnout score acceleration
        burnout_trend = trend_analysis.get("burnout_score_trend", {})
        if burnout_trend.get("direction") == "accelerating_increase":
            warnings.append("Burnout score is increasing at an accelerating rate")
        elif burnout_trend.get("slope", 0) > 0.5:
            warnings.append("Rapid increase in burnout score detected")
        
        # Check incident load trend
        incident_trend = trend_analysis.get("incident_load_trend", {})
        if incident_trend.get("direction") in ["increasing", "accelerating_increase"]:
            if incident_trend.get("current_value", 0) > incident_trend.get("mean_value", 0) * 1.5:
                warnings.append("Incident load significantly above historical average")
        
        # Check after-hours work
        after_hours_trend = trend_analysis.get("after_hours_trend", {})
        if after_hours_trend.get("current_value", 0) > 30:  # 30% threshold
            if after_hours_trend.get("direction") == "increasing":
                warnings.append("After-hours work increasing and already at concerning levels")
        
        # Check sentiment decline
        sentiment_trend = trend_analysis.get("sentiment_trend", {})
        if sentiment_trend.get("direction") in ["decreasing", "accelerating_decrease"]:
            warnings.append("Team sentiment showing concerning decline")
        
        # Check volatility
        high_volatility_metrics = [
            name for name, data in trend_analysis.items()
            if isinstance(data, dict) and data.get("volatility", 0) > 0.3
        ]
        if len(high_volatility_metrics) >= 2:
            warnings.append(f"High volatility in multiple metrics: {', '.join(high_volatility_metrics)}")
        
        # Check response time degradation
        response_trend = trend_analysis.get("response_time_trend", {})
        if response_trend.get("direction") == "increasing" and response_trend.get("current_value", 0) > 120:
            warnings.append("Response times increasing and exceeding 2-hour threshold")
        
        # Compound risk factors
        increasing_metrics = [
            name for name, data in trend_analysis.items()
            if isinstance(data, dict) and data.get("direction") in ["increasing", "accelerating_increase"]
            and name not in ["sentiment_trend"]  # Exclude inverse metrics
        ]
        if len(increasing_metrics) >= 3:
            warnings.append("Multiple risk factors trending upward simultaneously")
        
        return warnings
    
    def _calculate_critical_thresholds(
        self, 
        historical_analyses: List[Dict], 
        current_metrics: Dict
    ) -> Dict[str, Any]:
        """Calculate critical thresholds based on historical data."""
        thresholds = {}
        
        # Extract historical maximums that led to high burnout
        high_burnout_analyses = [
            a for a in historical_analyses 
            if a.get("burnout_score", 0) >= 7 or a.get("risk_level") == "high"
        ]
        
        if high_burnout_analyses:
            # Calculate thresholds based on high-burnout periods
            thresholds["incident_count"] = {
                "critical": statistics.mean([a.get("incident_count", 0) for a in high_burnout_analyses]),
                "warning": statistics.mean([a.get("incident_count", 0) for a in high_burnout_analyses]) * 0.8
            }
            
            thresholds["after_hours_percentage"] = {
                "critical": statistics.mean([a.get("after_hours_percentage", 0) for a in high_burnout_analyses]),
                "warning": 25.0  # Standard warning threshold
            }
            
            thresholds["response_time_minutes"] = {
                "critical": 180,  # 3 hours
                "warning": 120   # 2 hours
            }
        else:
            # Use standard thresholds if no historical high-burnout data
            thresholds = {
                "incident_count": {"critical": 20, "warning": 15},
                "after_hours_percentage": {"critical": 35, "warning": 25},
                "response_time_minutes": {"critical": 180, "warning": 120},
                "weekend_percentage": {"critical": 20, "warning": 15},
                "sentiment_score": {"critical": -0.3, "warning": -0.1}
            }
        
        # Check current metrics against thresholds
        for metric, threshold_values in thresholds.items():
            current_value = current_metrics.get(metric)
            if current_value is not None:
                if metric == "sentiment_score":  # Inverse metric
                    threshold_values["current_status"] = (
                        "critical" if current_value <= threshold_values["critical"]
                        else "warning" if current_value <= threshold_values["warning"]
                        else "normal"
                    )
                else:
                    threshold_values["current_status"] = (
                        "critical" if current_value >= threshold_values["critical"]
                        else "warning" if current_value >= threshold_values["warning"]
                        else "normal"
                    )
                threshold_values["current_value"] = current_value
        
        return thresholds
    
    def _predict_risk_trajectory(
        self, 
        trend_analysis: Dict[str, Any], 
        current_metrics: Dict[str, Any],
        time_horizon_days: int
    ) -> Dict[str, Any]:
        """Predict risk trajectory over the specified time horizon."""
        # Calculate composite risk score
        current_risk_score = current_metrics.get("burnout_score", 5) * 10  # Convert to 0-100 scale
        
        # Calculate trajectory based on trends
        risk_velocity = 0
        risk_acceleration = 0
        contributing_factors = []
        
        # Weight different factors
        weights = {
            "burnout_score_trend": 0.3,
            "incident_load_trend": 0.2,
            "after_hours_trend": 0.2,
            "sentiment_trend": 0.15,
            "response_time_trend": 0.15
        }
        
        for metric, weight in weights.items():
            trend = trend_analysis.get(metric, {})
            if trend.get("slope"):
                risk_velocity += trend["slope"] * weight * 10  # Scale factor
                
                if trend.get("acceleration"):
                    risk_acceleration += trend["acceleration"] * weight * 5
                
                if trend.get("direction") in ["increasing", "accelerating_increase"]:
                    contributing_factors.append(f"{metric.replace('_trend', '')} is {trend['direction']}")
        
        # Project future risk score
        days_factor = time_horizon_days / 30  # Normalize to monthly rate
        projected_risk_score = current_risk_score + (risk_velocity * days_factor) + (0.5 * risk_acceleration * days_factor ** 2)
        projected_risk_score = max(0, min(100, projected_risk_score))  # Clamp to 0-100
        
        # Determine trajectory
        if risk_acceleration > 0.5:
            trajectory = "rapidly_deteriorating"
        elif risk_velocity > 5:
            trajectory = "deteriorating"
        elif risk_velocity < -5:
            trajectory = "improving"
        elif abs(risk_velocity) < 2:
            trajectory = "stable"
        else:
            trajectory = "slowly_deteriorating"
        
        # Determine predicted risk level
        if projected_risk_score >= 70:
            predicted_level = "critical"
        elif projected_risk_score >= 50:
            predicted_level = "high"
        elif projected_risk_score >= 30:
            predicted_level = "medium"
        else:
            predicted_level = "low"
        
        # Calculate confidence based on data quality and volatility
        avg_volatility = statistics.mean([
            trend.get("volatility", 0) 
            for trend in trend_analysis.values() 
            if isinstance(trend, dict) and "volatility" in trend
        ])
        
        data_completeness = sum(
            1 for trend in trend_analysis.values() 
            if isinstance(trend, dict) and trend.get("data_points", 0) >= 5
        ) / len(trend_analysis)
        
        confidence = (1 - avg_volatility) * data_completeness * 0.8  # Max 80% confidence
        
        return {
            "predicted_risk_level": predicted_level,
            "risk_trajectory": trajectory,
            "current_risk_score": round(current_risk_score, 1),
            "projected_risk_score": round(projected_risk_score, 1),
            "risk_velocity": round(risk_velocity, 2),
            "risk_acceleration": round(risk_acceleration, 2),
            "confidence_score": round(confidence, 2),
            "contributing_factors": contributing_factors
        }
    
    def _generate_timeline_predictions(
        self, 
        trend_analysis: Dict[str, Any],
        current_metrics: Dict[str, Any],
        time_horizon_days: int
    ) -> Dict[str, Any]:
        """Generate timeline predictions for reaching critical thresholds."""
        timeline = {}
        
        for metric_name, trend in trend_analysis.items():
            if not isinstance(trend, dict) or trend.get("direction") == "insufficient_data":
                continue
                
            current_value = trend.get("current_value", 0)
            slope = trend.get("slope", 0)
            
            if abs(slope) < 0.01:  # Too small to predict
                continue
            
            # Define critical thresholds for each metric
            critical_thresholds = {
                "burnout_score_trend": 8.0,  # Out of 10
                "incident_load_trend": 25,   # Number of incidents
                "after_hours_trend": 40,     # Percentage
                "weekend_work_trend": 25,    # Percentage
                "response_time_trend": 240,  # Minutes (4 hours)
                "sentiment_trend": -0.5      # Sentiment score
            }
            
            threshold = critical_thresholds.get(metric_name)
            if threshold is None:
                continue
            
            # Calculate days to threshold
            if metric_name == "sentiment_trend":  # Inverse metric
                if slope < 0 and current_value > threshold:
                    days_to_threshold = (threshold - current_value) / slope
                else:
                    days_to_threshold = None
            else:
                if slope > 0 and current_value < threshold:
                    days_to_threshold = (threshold - current_value) / slope
                else:
                    days_to_threshold = None
            
            if days_to_threshold and 0 < days_to_threshold <= time_horizon_days * 2:
                timeline[metric_name.replace("_trend", "")] = {
                    "days_to_critical": round(days_to_threshold),
                    "expected_date": (datetime.now() + timedelta(days=days_to_threshold)).strftime("%Y-%m-%d"),
                    "current_value": round(current_value, 2),
                    "critical_threshold": threshold,
                    "rate_of_change": round(slope, 3)
                }
        
        return timeline
    
    def _generate_intervention_recommendations(self, predictions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate time-sensitive intervention recommendations."""
        recommendations = []
        
        # Immediate interventions for critical trajectory
        if predictions["risk_trajectory"] in ["rapidly_deteriorating", "deteriorating"]:
            recommendations.append({
                "urgency": "immediate",
                "timeframe": "within_48_hours",
                "action": "Emergency workload review and redistribution",
                "rationale": f"Risk score projected to reach {predictions['projected_risk_score']:.0f} with {predictions['risk_trajectory']} trajectory",
                "expected_impact": "Slow or reverse burnout progression"
            })
        
        # Timeline-based interventions
        timeline = predictions.get("predicted_timeline", {})
        
        # Find most urgent threshold
        urgent_metrics = sorted(
            [(metric, data["days_to_critical"]) for metric, data in timeline.items()],
            key=lambda x: x[1]
        )
        
        if urgent_metrics and urgent_metrics[0][1] <= 14:  # Within 2 weeks
            metric, days = urgent_metrics[0]
            recommendations.append({
                "urgency": "high",
                "timeframe": f"within_{days}_days",
                "action": f"Address {metric} before critical threshold",
                "rationale": f"{metric} will reach critical level in {days} days",
                "expected_impact": "Prevent escalation to critical burnout"
            })
        
        # Early warning interventions
        if len(predictions["early_warning_signals"]) >= 3:
            recommendations.append({
                "urgency": "medium",
                "timeframe": "within_1_week",
                "action": "Comprehensive team health assessment",
                "rationale": f"{len(predictions['early_warning_signals'])} early warning signals detected",
                "expected_impact": "Identify and address root causes"
            })
        
        # Preventive interventions
        if predictions["confidence_score"] >= 0.6 and predictions["predicted_risk_level"] in ["high", "critical"]:
            recommendations.append({
                "urgency": "medium",
                "timeframe": "within_2_weeks",
                "action": "Implement preventive measures based on trend analysis",
                "rationale": f"High confidence ({predictions['confidence_score']:.0%}) prediction of {predictions['predicted_risk_level']} risk",
                "expected_impact": "Reduce projected risk by 20-30%"
            })
        
        # Specific metric interventions
        critical_thresholds = predictions.get("critical_thresholds", {})
        for metric, threshold_data in critical_thresholds.items():
            if threshold_data.get("current_status") == "warning":
                recommendations.append({
                    "urgency": "low",
                    "timeframe": "within_1_month", 
                    "action": f"Monitor and optimize {metric.replace('_', ' ')}",
                    "rationale": f"Currently at warning level: {threshold_data.get('current_value')}",
                    "expected_impact": "Prevent progression to critical level"
                })
        
        # Sort by urgency
        urgency_order = {"immediate": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda x: urgency_order.get(x["urgency"], 4))
        
        return recommendations[:5]  # Return top 5 recommendations


def create_burnout_predictor_tool():
    """Factory function to create burnout predictor tool for smolagents."""
    tool = BurnoutPredictorTool()
    
    def burnout_predictor(
        historical_analyses: List[Dict[str, Any]],
        current_metrics: Dict[str, Any],
        time_horizon_days: int = 30
    ) -> Dict[str, Any]:
        """
        Predict future burnout risk using trend analysis and pattern recognition.
        
        Args:
            historical_analyses: List of past burnout analyses (ordered by date)
            current_metrics: Current burnout metrics and indicators
            time_horizon_days: Prediction time horizon in days (default: 30)
            
        Returns:
            Dictionary with risk predictions, early warnings, and intervention recommendations
        """
        return tool(historical_analyses, current_metrics, time_horizon_days)
    
    return burnout_predictor