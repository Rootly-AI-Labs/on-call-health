#!/usr/bin/env python3

import asyncio
import sqlite3
from app.services.burnout_analyzer import BurnoutAnalyzerService

async def test_status_tracking():
    """Test that status tracking is working"""
    
    # Get the token from database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT api_token FROM rootly_integrations 
        WHERE platform = 'pagerduty' AND user_id = 2
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("Error: No PagerDuty integration found")
        return
    
    api_token = result[0]
    
    # Create burnout analyzer for PagerDuty
    analyzer = BurnoutAnalyzerService(api_token, platform="pagerduty")
    
    # Run analysis
    analysis_result = await analyzer.analyze_burnout(time_range_days=30)
    
    # Check if status distribution is captured
    members = analysis_result["team_analysis"]["members"]
    if members:
        member = members[0]
        metrics = member.get("metrics", {})
        
        print(f"Member: {member['user_name']}")
        print(f"Total incidents: {member['incident_count']}")
        
        if "status_distribution" in metrics:
            print(f"Status distribution: {metrics['status_distribution']}")
        else:
            print("❌ Status distribution not found in metrics")
        
        if "severity_distribution" in metrics:
            print(f"Severity distribution: {metrics['severity_distribution']}")
        else:
            print("❌ Severity distribution not found in metrics")
    else:
        print("❌ No members found in analysis")

if __name__ == "__main__":
    asyncio.run(test_status_tracking())