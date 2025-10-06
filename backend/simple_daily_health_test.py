#!/usr/bin/env python3
"""
Simple unit test for daily health calculation functionality.
Tests just the calculation logic without requiring full app setup.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_individual_daily_health_score(
    daily_data: Dict[str, Any], 
    date_obj: datetime, 
    user_email: str,
    team_analysis: List[Dict[str, Any]]
) -> int:
    """
    Standalone version of the daily health score calculation for testing.
    
    Based on Copenhagen Burnout Inventory methodology and research on 
    incident response psychological impact.
    """
    try:
        # Start with healthy baseline
        base_health = 100
        
        # Extract metrics from daily data
        incident_count = daily_data.get("incident_count", 0)
        severity_weighted = daily_data.get("severity_weighted_count", 0.0)
        after_hours_count = daily_data.get("after_hours_count", 0)
        weekend_count = daily_data.get("weekend_count", 0)
        high_severity_count = daily_data.get("high_severity_count", 0)
        
        # 1. INCIDENT LOAD PENALTY (Primary Stressor)
        # Research: Each incident adds 8-15 points of stress depending on context
        incident_penalty = 0
        if incident_count > 0:
            # Base penalty per incident
            incident_penalty = incident_count * 8
            
            # Escalating penalty for high volume days (cognitive overload)
            if incident_count >= 5:
                incident_penalty += (incident_count - 4) * 5  # Extra penalty for overload
            elif incident_count >= 3:
                incident_penalty += (incident_count - 2) * 3  # Moderate escalation
        
        # 2. SEVERITY-WEIGHTED STRESS (Psychological Impact)
        # Research: SEV0/1 incidents have outsized psychological impact
        severity_penalty = 0
        if severity_weighted > 0:
            # Convert severity weight to stress impact
            if severity_weighted >= 15:  # SEV0 incident
                severity_penalty = 25  # Major psychological stress
            elif severity_weighted >= 12:  # SEV1 incident  
                severity_penalty = 20  # High stress
            elif severity_weighted >= 6:   # Multiple SEV2 or single SEV2
                severity_penalty = 12  # Moderate stress
            else:
                severity_penalty = max(0, int(severity_weighted * 2))  # Linear for lower severity
        
        # 3. WORK-LIFE BALANCE VIOLATIONS
        after_hours_penalty = after_hours_count * 8  # 8 points per after-hours incident
        weekend_penalty = weekend_count * 12        # 12 points per weekend incident (higher impact)
        
        # 4. CRITICAL INCIDENT MULTIPLIER
        # High severity incidents have compounding psychological effects
        critical_multiplier = 1.0
        if high_severity_count > 0:
            critical_multiplier = 1.0 + (high_severity_count * 0.15)  # 15% more stress per critical incident
        
        # 5. CONTEXTUAL FACTORS
        
        # Day of week adjustment (Mondays and Fridays are more stressful)
        day_penalty = 0
        weekday = date_obj.weekday()  # 0=Monday, 6=Sunday
        if weekday == 0:  # Monday
            day_penalty = 3 if incident_count > 0 else 0
        elif weekday == 4:  # Friday
            day_penalty = 2 if incident_count > 0 else 0
        elif weekday >= 5:  # Weekend
            day_penalty = 5 if incident_count > 0 else 0
        
        # Personal workload vs team average (if available)
        personal_load_penalty = 0
        try:
            # Find this user's overall incident load
            user_member = None
            for member in team_analysis:
                if member.get("user_email", "").lower() == user_email.lower():
                    user_member = member
                    break
            
            if user_member:
                user_total_incidents = user_member.get("incident_count", 0)
                team_avg_incidents = sum(m.get("incident_count", 0) for m in team_analysis) / len(team_analysis) if team_analysis else 0
                
                # If user is handling significantly more than average, add stress penalty
                if team_avg_incidents > 0 and user_total_incidents > team_avg_incidents * 1.5:
                    personal_load_penalty = 5  # High-load team member gets extra stress on incident days
                    
        except Exception as load_calc_error:
            logger.warning(f"Could not calculate personal load penalty for {user_email}: {load_calc_error}")
        
        # CALCULATE FINAL HEALTH SCORE
        total_penalty = (
            (incident_penalty + severity_penalty + after_hours_penalty + weekend_penalty) * critical_multiplier +
            day_penalty + personal_load_penalty
        )
        
        final_health_score = base_health - total_penalty
        
        # Apply bounds (10-100 range)
        final_health_score = max(10, min(100, int(final_health_score)))
        
        # Log detailed calculation for debugging (only for high-impact days)
        if incident_count > 0 or final_health_score < 70:
            logger.info(f"🩺 HEALTH_CALC for {user_email} on {date_obj.strftime('%Y-%m-%d')}: "
                       f"incidents={incident_count}, severity_wt={severity_weighted:.1f}, "
                       f"after_hours={after_hours_count}, weekend={weekend_count}, "
                       f"penalties: inc={incident_penalty}, sev={severity_penalty}, ah={after_hours_penalty}, we={weekend_penalty}, "
                       f"multiplier={critical_multiplier:.2f}, final_score={final_health_score}")
        
        return final_health_score
        
    except Exception as e:
        logger.error(f"Error calculating individual daily health score for {user_email}: {e}")
        # Fallback: if we have incidents, assume moderate stress; if not, assume healthy
        return 60 if daily_data.get("incident_count", 0) > 0 else 88

def test_health_calculation_scenarios():
    """Test various scenarios for the health calculation."""
    
    logger.info("🧪 TESTING HEALTH CALCULATION SCENARIOS")
    
    # Test team data
    team_analysis = [
        {"user_email": "alice@company.com", "incident_count": 15},
        {"user_email": "bob@company.com", "incident_count": 8},
        {"user_email": "charlie@company.com", "incident_count": 3}
    ]
    
    test_cases = [
        {
            "name": "Healthy day (no incidents)",
            "daily_data": {
                "incident_count": 0,
                "severity_weighted_count": 0.0,
                "after_hours_count": 0,
                "weekend_count": 0,
                "high_severity_count": 0
            },
            "expected_range": (80, 100),
            "user": "alice@company.com"
        },
        {
            "name": "Light workday (1 incident, SEV3)",
            "daily_data": {
                "incident_count": 1,
                "severity_weighted_count": 3.0,
                "after_hours_count": 0,
                "weekend_count": 0,
                "high_severity_count": 0
            },
            "expected_range": (70, 90),
            "user": "alice@company.com"
        },
        {
            "name": "Moderate stress day (3 incidents, one after-hours)",
            "daily_data": {
                "incident_count": 3,
                "severity_weighted_count": 9.0,
                "after_hours_count": 1,
                "weekend_count": 0,
                "high_severity_count": 0
            },
            "expected_range": (45, 70),
            "user": "alice@company.com"
        },
        {
            "name": "High stress day (5 incidents, SEV1 involved)",
            "daily_data": {
                "incident_count": 5,
                "severity_weighted_count": 27.0,  # Includes one SEV1 (12.0 weight)
                "after_hours_count": 2,
                "weekend_count": 0,
                "high_severity_count": 1
            },
            "expected_range": (15, 40),
            "user": "alice@company.com"
        },
        {
            "name": "Critical day (SEV0 incident on weekend)",
            "daily_data": {
                "incident_count": 2,
                "severity_weighted_count": 18.0,  # SEV0 = 15.0 weight
                "after_hours_count": 1,
                "weekend_count": 2,  # Both incidents on weekend
                "high_severity_count": 1
            },
            "expected_range": (10, 25),
            "user": "alice@company.com",
            "is_weekend": True
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        logger.info(f"\n📋 TEST CASE {i}: {test_case['name']}")
        
        # Create test date (weekend if specified)
        if test_case.get('is_weekend'):
            test_date = datetime(2025, 9, 14)  # A Sunday
        else:
            test_date = datetime(2025, 9, 10)  # A Wednesday
        
        # Calculate health score
        health_score = calculate_individual_daily_health_score(
            daily_data=test_case["daily_data"],
            date_obj=test_date,
            user_email=test_case["user"],
            team_analysis=team_analysis
        )
        
        # Check if score is in expected range
        expected_min, expected_max = test_case["expected_range"]
        
        logger.info(f"   📊 Result: {health_score}/100")
        logger.info(f"   🎯 Expected range: {expected_min}-{expected_max}")
        
        if expected_min <= health_score <= expected_max:
            logger.info("   ✅ PASS - Score is within expected range")
        else:
            logger.error("   ❌ FAIL - Score is outside expected range")
            all_passed = False
    
    return all_passed

def test_correlation_behavior():
    """Test that the calculation shows proper correlations."""
    
    logger.info("\n🔗 TESTING CORRELATION BEHAVIOR")
    
    team_analysis = [{"user_email": "test@company.com", "incident_count": 10}]
    test_date = datetime(2025, 9, 10)
    
    # Test increasing incident count
    incident_scores = []
    for incident_count in range(0, 8):
        daily_data = {
            "incident_count": incident_count,
            "severity_weighted_count": incident_count * 3.0,
            "after_hours_count": 0,
            "weekend_count": 0,
            "high_severity_count": 0
        }
        score = calculate_individual_daily_health_score(daily_data, test_date, "test@company.com", team_analysis)
        incident_scores.append((incident_count, score))
        logger.info(f"   📊 {incident_count} incidents → {score}/100 health")
    
    # Check that more incidents = lower health scores
    scores_declining = all(
        incident_scores[i][1] >= incident_scores[i+1][1] 
        for i in range(len(incident_scores)-1)
    )
    
    if scores_declining:
        logger.info("   ✅ PASS - Health scores decline with more incidents")
    else:
        logger.error("   ❌ FAIL - Health scores don't decline consistently")
        
    # Test severity impact
    logger.info("\n   Testing severity impact:")
    base_data = {"incident_count": 2, "after_hours_count": 0, "weekend_count": 0, "high_severity_count": 0}
    
    sev3_score = calculate_individual_daily_health_score(
        {**base_data, "severity_weighted_count": 6.0}, test_date, "test@company.com", team_analysis)
    sev1_score = calculate_individual_daily_health_score(
        {**base_data, "severity_weighted_count": 24.0, "high_severity_count": 1}, test_date, "test@company.com", team_analysis)
    
    logger.info(f"   📊 2 SEV3 incidents → {sev3_score}/100")
    logger.info(f"   📊 2 incidents (1 SEV1) → {sev1_score}/100")
    
    if sev1_score < sev3_score:
        logger.info("   ✅ PASS - High severity incidents cause more stress")
    else:
        logger.error("   ❌ FAIL - High severity impact not working")
        return False
        
    return scores_declining

if __name__ == "__main__":
    print("🧪 Simple Daily Health Calculation Test")
    print("=" * 50)
    
    try:
        # Test different scenarios
        scenarios_passed = test_health_calculation_scenarios()
        
        # Test correlations
        correlations_passed = test_correlation_behavior()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS:")
        print(f"   Health Calculation Scenarios: {'✅ PASS' if scenarios_passed else '❌ FAIL'}")
        print(f"   Correlation Behavior: {'✅ PASS' if correlations_passed else '❌ FAIL'}")
        
        if scenarios_passed and correlations_passed:
            print("\n🎉 ALL TESTS PASSED! Daily health calculation logic is working correctly.")
        else:
            print("\n❌ Some tests failed. Check the calculation logic.")
            
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()