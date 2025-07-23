#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from app.services.burnout_analyzer import BurnoutAnalyzerService

async def test_final_verification():
    """Final verification of status tracking functionality"""
    
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
        print("❌ Error: No PagerDuty integration found")
        return
    
    api_token = result[0]
    
    print("🔍 Running final burnout analysis verification...")
    print("=" * 60)
    
    try:
        # Create burnout analyzer for PagerDuty
        analyzer = BurnoutAnalyzerService(api_token, platform="pagerduty")
        
        # Run analysis
        analysis_result = await analyzer.analyze_burnout(time_range_days=30)
        
        # Check results
        members = analysis_result["team_analysis"]["members"]
        if not members:
            print("❌ No members found in analysis")
            return
        
        member = members[0]
        metrics = member.get("metrics", {})
        
        print(f"✅ Member: {member['user_name']}")
        print(f"✅ Total incidents: {member['incident_count']}")
        print(f"✅ Burnout score: {member['burnout_score']:.2f}")
        print(f"✅ Risk level: {member['risk_level']}")
        
        # Verify status distribution
        if "status_distribution" in metrics:
            status_dist = metrics['status_distribution']
            print(f"\n📊 Status Distribution:")
            total_status_incidents = 0
            for status, count in status_dist.items():
                print(f"   {status}: {count}")
                total_status_incidents += count
            
            print(f"\n✅ Status breakdown total: {total_status_incidents}")
            print(f"✅ Member incident count: {member['incident_count']}")
            
            if total_status_incidents == member['incident_count']:
                print("✅ STATUS VERIFICATION PASSED: All incidents accounted for in status breakdown")
            else:
                print("❌ STATUS VERIFICATION FAILED: Mismatch between total and status breakdown")
            
            # Check for expected values
            triggered = status_dist.get('triggered', 0)
            acknowledged = status_dist.get('acknowledged', 0)
            resolved = status_dist.get('resolved', 0)
            
            print(f"\n🎯 Expected vs Actual:")
            print(f"   Expected - Triggered: 29, Acknowledged: 12, Resolved: 0")
            print(f"   Actual   - Triggered: {triggered}, Acknowledged: {acknowledged}, Resolved: {resolved}")
            
            if triggered == 29 and acknowledged == 12:
                print("🎉 PERFECT MATCH: Status counts are exactly as expected!")
            else:
                print("⚠️ Status counts don't match expected values")
        else:
            print("❌ Status distribution not found in metrics")
        
        # Verify severity distribution
        if "severity_distribution" in metrics:
            severity_dist = metrics['severity_distribution']
            print(f"\n📊 Severity Distribution:")
            for severity, count in severity_dist.items():
                print(f"   {severity}: {count}")
        else:
            print("❌ Severity distribution not found in metrics")
            
        print(f"\n📈 Other metrics:")
        print(f"   After-hours percentage: {metrics.get('after_hours_percentage', 'N/A')}")
        print(f"   Weekend percentage: {metrics.get('weekend_percentage', 'N/A')}")
        print(f"   Average response time: {metrics.get('avg_response_time_minutes', 'N/A')} minutes")
        
        # Save the analysis for manual inspection
        with open('final_analysis_verification.json', 'w') as f:
            json.dump(analysis_result, f, indent=2, default=str)
        print(f"\n💾 Full analysis saved to: final_analysis_verification.json")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_final_verification())