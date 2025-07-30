#!/usr/bin/env python3
"""
Debug script to identify why the health trends chart is only showing 2 data points
when there should be 3 (or more).

This script simulates the exact API logic and checks all possible issues.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from collections import defaultdict

def debug_trends_issue():
    """Debug the trends data issue comprehensively"""
    
    print("🔍 DEBUGGING HEALTH TRENDS CHART ISSUE")
    print("=" * 60)
    
    # Connect to database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Check who the primary user is (user with most data)
    cursor.execute('''
        SELECT user_id, COUNT(*) as count 
        FROM analyses 
        WHERE status = "completed" AND results IS NOT NULL 
        GROUP BY user_id 
        ORDER BY count DESC
    ''')
    user_stats = cursor.fetchall()
    
    print("📊 USER ANALYSIS COUNTS:")
    for user_id, count in user_stats:
        print(f"   User {user_id}: {count} completed analyses")
    
    primary_user_id = user_stats[0][0] if user_stats else 2
    print(f"   Primary user for testing: {primary_user_id}\n")
    
    # Get the most recent analysis for time_range context
    cursor.execute('''
        SELECT time_range, created_at 
        FROM analyses 
        WHERE user_id = ? AND status = "completed" AND results IS NOT NULL 
        ORDER BY created_at DESC 
        LIMIT 1
    ''', (primary_user_id,))
    
    recent_analysis = cursor.fetchone()
    if recent_analysis:
        recent_time_range, recent_date = recent_analysis
        print(f"📅 MOST RECENT ANALYSIS:")
        print(f"   Date: {recent_date}")
        print(f"   Time range: {recent_time_range} days\n")
    else:
        recent_time_range = 30
        print("❌ No recent analysis found, using default 30 days\n")
    
    # Test different scenarios that the frontend might be using
    test_scenarios = [
        {
            'name': 'Frontend Default (No integration filter, recent time_range)',
            'user_id': primary_user_id,
            'integration_id': None,
            'days_back': recent_time_range or 30
        },
        {
            'name': 'Frontend Default (No integration filter, 14 days)',
            'user_id': primary_user_id,
            'integration_id': None,
            'days_back': 14
        },
        {
            'name': 'With Integration 3 Filter (14 days)',
            'user_id': primary_user_id,
            'integration_id': 3,
            'days_back': 14
        },
        {
            'name': 'With Integration 4 Filter (14 days)', 
            'user_id': primary_user_id,
            'integration_id': 4,
            'days_back': 14
        }
    ]
    
    for i, scenario in enumerate(test_scenarios):
        print(f"🧪 TEST {i+1}: {scenario['name']}")
        print("-" * 50)
        
        result = simulate_get_historical_trends(
            cursor,
            user_id=scenario['user_id'],
            integration_id=scenario['integration_id'],
            days_back=scenario['days_back']
        )
        
        print(f"   📊 Result: {result['daily_trends_count']} daily trend points")
        print(f"   📅 Date range: {result['date_range']['start']} to {result['date_range']['end']}")
        print(f"   📋 Daily breakdown:")
        
        for date, info in result['daily_breakdown'].items():
            print(f"      {date}: {info['count']} analyses, avg_score={info['avg_score']:.2f}")
        
        if result['daily_trends_count'] == 2:
            print("   ⚠️  THIS MATCHES THE FRONTEND ISSUE (2 data points)")
        elif result['daily_trends_count'] == 0:
            print("   ❌ NO DATA - would show empty chart")
        else:
            print(f"   ✅ Would show {result['daily_trends_count']} data points")
        
        print()
    
    # Check for specific data quality issues
    print("🔬 DATA QUALITY ANALYSIS")
    print("-" * 30)
    
    # Check for analyses with invalid team_health structure
    cursor.execute('''
        SELECT id, created_at, results 
        FROM analyses 
        WHERE user_id = ? AND status = "completed" AND results IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 20
    ''', (primary_user_id,))
    
    recent_analyses = cursor.fetchall()
    print(f"📊 Checking last {len(recent_analyses)} analyses for data quality issues:\n")
    
    valid_count = 0
    invalid_count = 0
    
    for analysis_id, created_at, results_json in recent_analyses:
        try:
            results = json.loads(results_json)
            team_health = results.get('team_health', {})
            
            if not team_health:
                print(f"   ❌ Analysis #{analysis_id} ({created_at}): Missing team_health")
                invalid_count += 1
                continue
                
            required_fields = ['overall_score', 'average_burnout_score', 'members_at_risk', 'health_status']
            missing_fields = [field for field in required_fields if field not in team_health]
            
            if missing_fields:
                print(f"   ⚠️  Analysis #{analysis_id} ({created_at}): Missing fields {missing_fields}")
                invalid_count += 1
            else:
                valid_count += 1
                
        except json.JSONDecodeError:
            print(f"   ❌ Analysis #{analysis_id} ({created_at}): Invalid JSON")
            invalid_count += 1
    
    print(f"\n📊 Data Quality Summary:")
    print(f"   ✅ Valid analyses: {valid_count}")
    print(f"   ❌ Invalid analyses: {invalid_count}")
    
    if invalid_count > 0:
        print("   ⚠️  Data quality issues found - these analyses would be skipped")
    
    conn.close()

def simulate_get_historical_trends(cursor, user_id, integration_id=None, days_back=14):
    """Simulate the exact get_historical_trends API logic"""
    
    # Calculate date range exactly like API
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Build query exactly like API
    query = '''
        SELECT id, created_at, results, rootly_integration_id 
        FROM analyses 
        WHERE user_id = ? 
          AND status = "completed" 
          AND results IS NOT NULL 
          AND created_at >= ? 
          AND created_at <= ?
    '''
    
    params = [user_id, start_date.isoformat(), end_date.isoformat()]
    
    if integration_id:
        query += ' AND rootly_integration_id = ?'
        params.append(integration_id)
    
    query += ' ORDER BY created_at ASC'
    
    cursor.execute(query, params)
    analyses = cursor.fetchall()
    
    # Process exactly like the API
    daily_data = defaultdict(list)
    
    for analysis_id, created_at_str, results_json, integration_id_result in analyses:
        # Parse date exactly like API
        try:
            created_at = datetime.fromisoformat(
                created_at_str.replace('Z', '+00:00') if created_at_str.endswith('Z') else created_at_str
            )
        except ValueError:
            # Handle different datetime formats
            created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M:%S')
        
        analysis_date = created_at.strftime('%Y-%m-%d')
        
        # Parse results exactly like API
        try:
            results = json.loads(results_json)
            team_health = results.get('team_health', {})
            
            if not team_health:
                continue
                
            # Extract metrics exactly like API
            overall_score = team_health.get('overall_score', 0.0)
            average_burnout_score = team_health.get('average_burnout_score', 0.0)
            members_at_risk = team_health.get('members_at_risk', 0)
            health_status = team_health.get('health_status', 'unknown')
            
            # Count total members exactly like API
            team_analysis = results.get('team_analysis', [])
            if isinstance(team_analysis, dict):
                team_analysis = team_analysis.get('members', [])
            total_members = len(team_analysis) if isinstance(team_analysis, list) else 0
            
            daily_data[analysis_date].append({
                'overall_score': float(overall_score),
                'average_burnout_score': float(average_burnout_score),
                'members_at_risk': int(members_at_risk),
                'total_members': int(total_members),
                'health_status': str(health_status),
                'analysis_id': analysis_id
            })
            
        except json.JSONDecodeError:
            continue
    
    # Calculate daily averages exactly like API
    daily_breakdown = {}
    for date in sorted(daily_data.keys()):
        day_analyses = daily_data[date]
        avg_overall = sum(a['overall_score'] for a in day_analyses) / len(day_analyses)
        
        daily_breakdown[date] = {
            'count': len(day_analyses),
            'avg_score': avg_overall
        }
    
    return {
        'daily_trends_count': len(daily_data),
        'total_analyses': len(analyses),
        'date_range': {
            'start': start_date.strftime('%Y-%m-%d'),
            'end': end_date.strftime('%Y-%m-%d')
        },
        'daily_breakdown': daily_breakdown
    }

if __name__ == "__main__":
    debug_trends_issue()