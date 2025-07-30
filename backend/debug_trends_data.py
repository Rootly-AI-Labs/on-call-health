"""
Debug script to check historical trends data and understand why only 2 data points show
"""
import sqlite3
from datetime import datetime, timedelta

def debug_trends_data():
    """Debug historical trends data"""
    
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    # Get current date range (14 days back like the API)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=14)
    
    print(f"=== DEBUGGING TRENDS DATA ===")
    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print()
    
    # Check all completed analyses in the last 14 days
    cursor.execute("""
        SELECT id, user_id, rootly_integration_id, created_at, status, 
               json_extract(results, '$.team_health.overall_score') as overall_score,
               json_extract(results, '$.team_health.members_at_risk') as members_at_risk
        FROM analyses 
        WHERE status = 'completed' 
        AND results IS NOT NULL 
        AND created_at >= ?
        ORDER BY created_at DESC
    """, (start_date.strftime('%Y-%m-%d %H:%M:%S'),))
    
    analyses = cursor.fetchall()
    
    print(f"=== ALL COMPLETED ANALYSES (last 14 days) ===")
    print(f"Total: {len(analyses)} analyses")
    print()
    
    integration_data = {}
    date_data = {}
    
    for analysis in analyses:
        analysis_id, user_id, integration_id, created_at, status, overall_score, members_at_risk = analysis
        analysis_date = created_at[:10]  # Extract date part
        
        print(f"Analysis {analysis_id}: Integration {integration_id}, Date {analysis_date}, Score {overall_score}, At Risk {members_at_risk}")
        
        # Group by integration
        if integration_id not in integration_data:
            integration_data[integration_id] = []
        integration_data[integration_id].append({
            'date': analysis_date,
            'score': overall_score,
            'at_risk': members_at_risk
        })
        
        # Group by date (all integrations)
        if analysis_date not in date_data:
            date_data[analysis_date] = []
        date_data[analysis_date].append({
            'integration': integration_id,
            'score': overall_score,
            'at_risk': members_at_risk
        })
    
    print()
    print(f"=== BY INTEGRATION ===")
    for integration_id, data in integration_data.items():
        unique_dates = set(item['date'] for item in data)
        print(f"Integration {integration_id}: {len(unique_dates)} unique dates - {sorted(unique_dates)}")
    
    print()
    print(f"=== BY DATE (ALL INTEGRATIONS) ===")
    for date, data in sorted(date_data.items()):
        integrations = set(item['integration'] for item in data if item['integration'] is not None)
        avg_score = sum(float(item['score'] or 0) for item in data) / len(data)
        print(f"Date {date}: {len(data)} analyses from integrations {sorted(integrations)}, avg score: {avg_score:.1f}")
    
    print()
    print(f"=== EXPECTED TREND POINTS ===")
    print(f"All integrations combined: {len(date_data)} data points")
    print(f"Integration 3 only: {len(set(item['date'] for item in integration_data.get(3, [])))} data points")
    print(f"Integration 4 only: {len(set(item['date'] for item in integration_data.get(4, [])))} data points")
    
    conn.close()

if __name__ == "__main__":
    debug_trends_data()