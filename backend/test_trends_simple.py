#!/usr/bin/env python3
"""
Simple test to check trends data processing logic from database
"""
import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

def test_historical_trends_logic():
    """Test the logic that would be used in the /trends/historical endpoint"""
    
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Simulate the same query logic from the endpoint
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Get completed analyses within date range (same as endpoint logic)
    cursor.execute('''
        SELECT id, user_id, rootly_integration_id, created_at, results 
        FROM analyses 
        WHERE status = 'completed'
        AND created_at >= ?
        AND created_at <= ?
        AND results IS NOT NULL
        ORDER BY created_at ASC
    ''', (start_date.isoformat(), end_date.isoformat()))
    
    analyses = cursor.fetchall()
    print(f"\nFound {len(analyses)} completed analyses in date range")
    
    if not analyses:
        print("❌ NO ANALYSES FOUND - This explains why daily_trends is empty!")
        return
    
    # Process analyses like the endpoint does
    daily_data = defaultdict(list)
    
    for analysis_id, user_id, integration_id, created_at, results_json in analyses:
        analysis_date = datetime.fromisoformat(created_at).strftime("%Y-%m-%d")
        print(f"\nProcessing analysis {analysis_id} from {analysis_date}")
        
        try:
            results = json.loads(results_json)
        except json.JSONDecodeError:
            print(f"  ❌ Invalid JSON in results")
            continue
            
        if not isinstance(results, dict):
            print(f"  ❌ Results is not a dict: {type(results)}")
            continue
            
        team_health = results.get("team_health", {})
        if not team_health:
            print(f"  ❌ No team_health data")
            continue
            
        print(f"  ✅ Has team_health data")
        
        # Extract metrics like the endpoint does
        overall_score = team_health.get("overall_score", 0.0)
        average_burnout_score = team_health.get("average_burnout_score", 0.0) 
        members_at_risk = team_health.get("members_at_risk", 0)
        health_status = team_health.get("health_status", "unknown")
        
        # Count total members from team_analysis
        team_analysis = results.get("team_analysis", {})
        if isinstance(team_analysis, dict):
            members = team_analysis.get("members", [])
            total_members = len(members) if isinstance(members, list) else 0
        else:
            total_members = 0
        
        print(f"     overall_score: {overall_score}")
        print(f"     members_at_risk: {members_at_risk}")
        print(f"     total_members: {total_members}")
        print(f"     health_status: {health_status}")
        
        daily_data[analysis_date].append({
            "overall_score": float(overall_score),
            "average_burnout_score": float(average_burnout_score),
            "members_at_risk": int(members_at_risk),
            "total_members": int(total_members),
            "health_status": str(health_status)
        })
    
    # Calculate daily averages like the endpoint does
    daily_trends = []
    
    for date in sorted(daily_data.keys()):
        day_analyses = daily_data[date]
        
        # Calculate averages for the day
        avg_overall = sum(a["overall_score"] for a in day_analyses) / len(day_analyses)
        avg_burnout = sum(a["average_burnout_score"] for a in day_analyses) / len(day_analyses)
        avg_at_risk = sum(a["members_at_risk"] for a in day_analyses) / len(day_analyses)
        avg_total = sum(a["total_members"] for a in day_analyses) / len(day_analyses)
        
        # Use most common health status for the day
        status_counts = defaultdict(int)
        for a in day_analyses:
            status_counts[a["health_status"]] += 1
        most_common_status = max(status_counts.items(), key=lambda x: x[1])[0]
        
        daily_trend = {
            "date": date,
            "overall_score": round(avg_overall, 2),
            "average_burnout_score": round(avg_burnout, 2),
            "members_at_risk": round(avg_at_risk),
            "total_members": round(avg_total),
            "health_status": most_common_status,
            "analysis_count": len(day_analyses)
        }
        
        daily_trends.append(daily_trend)
        
        print(f"\n✅ Daily trend for {date}:")
        print(f"   score: {daily_trend['overall_score']}")
        print(f"   at_risk: {daily_trend['members_at_risk']}")
        print(f"   analyses: {daily_trend['analysis_count']}")
    
    print(f"\n🎯 FINAL RESULT: {len(daily_trends)} daily trend points created")
    
    if daily_trends:
        print("✅ Daily trends data would be populated!")
    else:
        print("❌ Daily trends would still be empty!")
    
    conn.close()
    return daily_trends

if __name__ == "__main__":
    print("=== TESTING HISTORICAL TRENDS LOGIC ===")
    trends = test_historical_trends_logic()