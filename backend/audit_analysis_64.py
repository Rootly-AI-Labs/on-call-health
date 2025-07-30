#!/usr/bin/env python3
"""
Data consistency audit script for analysis ID 64.
"""
import json
import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.models.analysis import Analysis

def connect_to_database():
    """Connect to the database and return session."""
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
    
    # Handle SQLite URL format for SQLAlchemy 2.0+
    if DATABASE_URL.startswith("sqlite"):
        engine = create_engine(
            DATABASE_URL, 
            connect_args={"check_same_thread": False},
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=300
        )
    else:
        engine = create_engine(
            DATABASE_URL,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=300
        )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def extract_analysis_data(analysis_id=112):
    """Extract and analyze data from analysis ID 64."""
    db = connect_to_database()
    
    try:
        # Query analysis ID 64
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            print(f"Analysis ID {analysis_id} not found!")
            return None
        
        print(f"=== ANALYSIS {analysis_id} BASIC INFO ===")
        print(f"ID: {analysis.id}")
        print(f"UUID: {analysis.uuid}")
        print(f"Status: {analysis.status}")
        print(f"Time Range: {analysis.time_range} days")
        print(f"Created: {analysis.created_at}")
        print(f"Completed: {analysis.completed_at}")
        print()
        
        if not analysis.results:
            print("No results data found!")
            return None
        
        results = analysis.results
        return results
        
    finally:
        db.close()

def analyze_data_consistency(results):
    """Perform comprehensive data consistency analysis."""
    print("=== DATA CONSISTENCY AUDIT REPORT ===")
    print()
    
    # Initialize counters
    inconsistencies = []
    
    # 1. Extract metadata totals
    metadata = results.get('metadata', {})
    metadata_total = metadata.get('total_incidents', 0)
    analysis_period_days = metadata.get('analysis_period_days', 0)
    start_date = metadata.get('start_date', '')
    end_date = metadata.get('end_date', '')
    
    print(f"1. METADATA ANALYSIS:")
    print(f"   Total Incidents (metadata): {metadata_total}")
    print(f"   Analysis Period: {analysis_period_days} days")
    print(f"   Date Range: {start_date} to {end_date}")
    print()
    
    # 2. Analyze daily trends
    daily_trends = results.get('daily_trends', [])
    daily_incident_sum = sum(day.get('incident_count', 0) for day in daily_trends)
    daily_trend_days = len(daily_trends)
    
    print(f"2. DAILY TRENDS ANALYSIS:")
    print(f"   Number of daily trend data points: {daily_trend_days}")
    print(f"   Total incidents (sum of daily trends): {daily_incident_sum}")
    print(f"   Expected data points (analysis period): {analysis_period_days}")
    
    # Check date consistency in daily trends
    if daily_trends:
        first_date = daily_trends[0].get('date', '')
        last_date = daily_trends[-1].get('date', '')
        print(f"   First date in trends: {first_date}")
        print(f"   Last date in trends: {last_date}")
        
        # Check for realistic incident distribution
        incident_counts = [day.get('incident_count', 0) for day in daily_trends]
        max_incidents = max(incident_counts) if incident_counts else 0
        min_incidents = min(incident_counts) if incident_counts else 0
        avg_incidents = sum(incident_counts) / len(incident_counts) if incident_counts else 0
        print(f"   Daily incident range: {min_incidents} - {max_incidents} (avg: {avg_incidents:.1f})")
        
        # Check if it's realistic data (not 1 per day)
        unique_counts = len(set(incident_counts))
        print(f"   Unique incident count values: {unique_counts}")
        if unique_counts == 1 and incident_counts[0] == 1:
            inconsistencies.append("Daily trends show exactly 1 incident per day (likely fallback/demo data)")
    
    print()
    
    # 3. Analyze team analysis data
    team_analysis = results.get('team_analysis', {})
    members = team_analysis.get('members', [])
    team_incident_sum = sum(member.get('incident_count', 0) for member in members)
    member_count = len(members)
    
    print(f"3. TEAM ANALYSIS:")
    print(f"   Number of team members: {member_count}")
    print(f"   Total incidents (sum from members): {team_incident_sum}")
    
    if members:
        member_incident_counts = [member.get('incident_count', 0) for member in members]
        max_member_incidents = max(member_incident_counts)
        min_member_incidents = min(member_incident_counts)
        avg_member_incidents = sum(member_incident_counts) / len(member_incident_counts)
        print(f"   Member incident range: {min_member_incidents} - {max_member_incidents} (avg: {avg_member_incidents:.1f})")
        
        # Show top 5 members by incident count
        sorted_members = sorted(members, key=lambda x: x.get('incident_count', 0), reverse=True)
        print(f"   Top 5 members by incident count:")
        for i, member in enumerate(sorted_members[:5]):
            name = member.get('name', 'Unknown')
            incidents = member.get('incident_count', 0)
            print(f"     {i+1}. {name}: {incidents} incidents")
    
    print()
    
    # 4. Analyze severity breakdown
    severity_breakdown = results.get('severity_breakdown', {})
    sev_totals = {}
    sev_sum = 0
    
    print(f"4. SEVERITY BREAKDOWN:")
    for sev_level, count in severity_breakdown.items():
        if isinstance(count, (int, float)):
            sev_totals[sev_level] = count
            sev_sum += count
            print(f"   {sev_level}: {count}")
    
    print(f"   Total (severity sum): {sev_sum}")
    print()
    
    # 5. Check for consistency across all sources
    print("5. CONSISTENCY CHECK:")
    all_totals = {
        'metadata': metadata_total,
        'daily_trends': daily_incident_sum,
        'team_analysis': team_incident_sum,
        'severity_breakdown': sev_sum
    }
    
    expected_total = 2841  # Based on analysis ID 112
    print(f"   Expected total (user report): {expected_total}")
    
    for source, total in all_totals.items():
        status = "✓ MATCH" if total == expected_total else "✗ MISMATCH"
        print(f"   {source}: {total} - {status}")
        
        if total != expected_total:
            inconsistencies.append(f"{source} total ({total}) does not match expected ({expected_total})")
    
    # Check if all sources match each other
    unique_totals = set(all_totals.values())
    if len(unique_totals) == 1:
        print(f"   All sources consistent: ✓ YES")
    else:
        print(f"   All sources consistent: ✗ NO - Found {len(unique_totals)} different totals")
        inconsistencies.append(f"Inconsistent totals across sources: {unique_totals}")
    
    print()
    
    # 6. Data quality assessment
    print("6. DATA QUALITY ASSESSMENT:")
    
    # Check if this looks like real data vs fallback/demo data
    is_real_data = True
    quality_issues = []
    
    # Check date ranges
    if start_date and end_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            actual_days = (end_dt - start_dt).days + 1
            
            if actual_days != analysis_period_days:
                quality_issues.append(f"Date range mismatch: {actual_days} actual vs {analysis_period_days} expected days")
                
            # Check if dates are realistic (not too old or future)
            now = datetime.now()
            if start_dt > now:
                quality_issues.append("Start date is in the future")
            if (now - end_dt).days > 365:
                quality_issues.append("Analysis is more than 1 year old")
                
        except Exception as e:
            quality_issues.append(f"Invalid date format: {e}")
    
    # Check for realistic data patterns
    if daily_trends:
        # Check if all days have exactly 1 incident (demo data pattern)
        all_ones = all(day.get('incident_count', 0) == 1 for day in daily_trends)
        if all_ones:
            quality_issues.append("All days have exactly 1 incident (likely demo/fallback data)")
            is_real_data = False
        
        # Check for missing days
        if daily_trend_days < analysis_period_days * 0.8:  # Less than 80% coverage
            quality_issues.append(f"Missing daily data: only {daily_trend_days}/{analysis_period_days} days covered")
    
    # Check team member data realism
    if members:
        # Check for generic/placeholder names
        generic_names = ['User', 'Member', 'Test', 'Demo', 'Example']
        placeholder_count = sum(1 for member in members if any(generic in member.get('name', '') for generic in generic_names))
        if placeholder_count > member_count * 0.3:  # More than 30% generic names
            quality_issues.append(f"High number of generic/placeholder member names: {placeholder_count}/{member_count}")
            is_real_data = False
    
    print(f"   Appears to be real data: {'✓ YES' if is_real_data else '✗ NO (likely demo/fallback)'}")
    
    if quality_issues:
        print(f"   Quality issues found:")
        for issue in quality_issues:
            print(f"     - {issue}")
    else:
        print(f"   No quality issues detected")
    
    print()
    
    # 7. Summary
    print("7. SUMMARY:")
    if inconsistencies:
        print(f"   ✗ {len(inconsistencies)} INCONSISTENCIES FOUND:")
        for issue in inconsistencies:
            print(f"     - {issue}")
    else:
        print(f"   ✓ NO MAJOR INCONSISTENCIES FOUND")
    
    if quality_issues:
        print(f"   ✗ {len(quality_issues)} QUALITY ISSUES FOUND:")
        for issue in quality_issues:
            print(f"     - {issue}")
    else:
        print(f"   ✓ NO QUALITY ISSUES FOUND")
    
    return {
        'metadata': metadata,
        'totals': all_totals,
        'inconsistencies': inconsistencies,
        'quality_issues': quality_issues,
        'is_real_data': is_real_data,
        'daily_trends_count': daily_trend_days,
        'member_count': member_count
    }

def main():
    """Main audit function."""
    analysis_id = 112  # Using ID 112 as it has high incident count (2841)
    print(f"Starting data consistency audit for Analysis ID {analysis_id}...")
    print("=" * 60)
    print()
    
    # Extract analysis data
    results = extract_analysis_data(analysis_id)
    
    if results:
        # Perform consistency analysis
        audit_results = analyze_data_consistency(results)
        
        # Optional: Save detailed results to file
        with open(f'analysis_{analysis_id}_audit_results.json', 'w') as f:
            json.dump({
                'analysis_results': results,
                'audit_summary': audit_results
            }, f, indent=2, default=str)
        
        print()
        print(f"Detailed analysis results saved to: analysis_{analysis_id}_audit_results.json")
    else:
        print("Failed to extract analysis data.")

if __name__ == "__main__":
    main()