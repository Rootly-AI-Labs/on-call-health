#!/usr/bin/env python3
"""
Comprehensive analysis audit to find data structure patterns and inconsistencies.
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

def analyze_multiple_analyses():
    """Analyze multiple analyses to understand data structure patterns."""
    db = connect_to_database()
    
    try:
        # Query recent completed analyses with results
        analyses = db.query(Analysis).filter(
            Analysis.status == 'completed',
            Analysis.results.isnot(None)
        ).order_by(Analysis.id.desc()).limit(10).all()
        
        if not analyses:
            print("No completed analyses with results found!")
            return
        
        print("=== COMPREHENSIVE ANALYSIS STRUCTURE AUDIT ===")
        print()
        print(f"Examining {len(analyses)} recent completed analyses...")
        print()
        
        structure_patterns = {}
        
        for i, analysis in enumerate(analyses):
            print(f"--- ANALYSIS {analysis.id} ---")
            print(f"UUID: {analysis.uuid}")
            print(f"Time Range: {analysis.time_range} days")
            print(f"Created: {analysis.created_at}")
            print(f"Completed: {analysis.completed_at}")
            
            if not analysis.results:
                print("No results data")
                continue
            
            results = analysis.results
            
            # Analyze structure
            top_level_keys = set(results.keys())
            structure_patterns[analysis.id] = {
                'keys': top_level_keys,
                'metadata': {},
                'daily_trends': None,
                'team_analysis': None,
                'inconsistencies': []
            }
            
            print(f"Top-level structure keys: {sorted(top_level_keys)}")
            
            # Check metadata
            metadata = results.get('metadata', {})
            if metadata:
                total_incidents = metadata.get('total_incidents', 0)
                analysis_period = metadata.get('analysis_period_days', metadata.get('days_analyzed', 0))
                start_date = metadata.get('start_date', metadata.get('date_range', {}).get('start', ''))
                end_date = metadata.get('end_date', metadata.get('date_range', {}).get('end', ''))
                
                structure_patterns[analysis.id]['metadata'] = {
                    'total_incidents': total_incidents,
                    'analysis_period': analysis_period,
                    'start_date': start_date,
                    'end_date': end_date
                }
                
                print(f"  Metadata: {total_incidents} incidents, {analysis_period} days")
                print(f"  Date range: {start_date} to {end_date}")
            
            # Check for daily trends
            daily_trends = results.get('daily_trends', [])
            if daily_trends:
                daily_count = len(daily_trends)
                daily_incident_sum = sum(day.get('incident_count', 0) for day in daily_trends)
                structure_patterns[analysis.id]['daily_trends'] = {
                    'count': daily_count,
                    'incident_sum': daily_incident_sum
                }
                print(f"  Daily trends: {daily_count} data points, {daily_incident_sum} total incidents")
            else:
                print(f"  Daily trends: MISSING or EMPTY")
            
            # Check team analysis
            team_analysis = results.get('team_analysis', {})
            if team_analysis:
                members = team_analysis.get('members', [])
                team_incident_sum = sum(member.get('incident_count', 0) for member in members)
                structure_patterns[analysis.id]['team_analysis'] = {
                    'member_count': len(members),
                    'incident_sum': team_incident_sum
                }
                print(f"  Team analysis: {len(members)} members, {team_incident_sum} total incidents")
            
            # Check severity breakdown
            severity_breakdown = results.get('severity_breakdown', {})
            if severity_breakdown:
                sev_sum = sum(count for count in severity_breakdown.values() if isinstance(count, (int, float)))
                print(f"  Severity breakdown: {sev_sum} total incidents")
            
            # Quick consistency check
            metadata_total = structure_patterns[analysis.id]['metadata'].get('total_incidents', 0)
            daily_total = structure_patterns[analysis.id]['daily_trends']['incident_sum'] if structure_patterns[analysis.id]['daily_trends'] else 0
            team_total = structure_patterns[analysis.id]['team_analysis']['incident_sum'] if structure_patterns[analysis.id]['team_analysis'] else 0
            
            inconsistencies = []
            if daily_total > 0 and daily_total != metadata_total:
                inconsistencies.append(f"Daily trends ({daily_total}) != metadata ({metadata_total})")
            if team_total > 0 and team_total != metadata_total:
                inconsistencies.append(f"Team analysis ({team_total}) != metadata ({metadata_total})")
            
            if inconsistencies:
                print(f"  Inconsistencies: {', '.join(inconsistencies)}")
                structure_patterns[analysis.id]['inconsistencies'] = inconsistencies
            else:
                print(f"  Consistency: OK")
            
            print()
        
        # Summary analysis
        print("=== STRUCTURE PATTERN SUMMARY ===")
        print()
        
        # Count which analyses have daily_trends
        has_daily_trends = sum(1 for p in structure_patterns.values() if p['daily_trends'] is not None)
        has_team_analysis = sum(1 for p in structure_patterns.values() if p['team_analysis'] is not None)
        has_inconsistencies = sum(1 for p in structure_patterns.values() if p['inconsistencies'])
        
        print(f"Analyses with daily_trends: {has_daily_trends}/{len(structure_patterns)}")
        print(f"Analyses with team_analysis: {has_team_analysis}/{len(structure_patterns)}")
        print(f"Analyses with inconsistencies: {has_inconsistencies}/{len(structure_patterns)}")
        print()
        
        # Show common structure keys
        all_keys = set()
        for pattern in structure_patterns.values():
            all_keys.update(pattern['keys'])
        
        print(f"All unique top-level keys found: {sorted(all_keys)}")
        print()
        
        # Show problematic analyses
        problematic = [(aid, p) for aid, p in structure_patterns.items() if p['inconsistencies'] or p['daily_trends'] is None]
        
        if problematic:
            print("PROBLEMATIC ANALYSES:")
            for analysis_id, pattern in problematic:
                print(f"  ID {analysis_id}:")
                if pattern['daily_trends'] is None:
                    print(f"    - Missing daily_trends data")
                for inconsistency in pattern['inconsistencies']:
                    print(f"    - {inconsistency}")
        
        print()
        print("=== HEALTH TRENDS CHART ISSUE CONFIRMATION ===")
        print()
        
        if has_daily_trends == 0:
            print("✗ CRITICAL: NO analyses have daily_trends data!")
            print("  This confirms the health trends chart issue described in CLAUDE.md")
            print("  The chart cannot show daily incident trends because the data doesn't exist")
        elif has_daily_trends < len(structure_patterns):
            print(f"⚠ WARNING: Only {has_daily_trends}/{len(structure_patterns)} analyses have daily_trends data")
            print("  This suggests inconsistent data structure across analyses")
        else:
            print("✓ All analyses have daily_trends data")
        
        print()
        print("RECOMMENDED ACTIONS:")
        print("1. Fix the analysis pipeline to consistently generate daily_trends data")
        print("2. Ensure daily_trends contains daily breakdown of incidents over the analysis period")
        print("3. Update the health trends chart to use daily_trends instead of historical analysis results")
        print("4. Add data validation to ensure consistency between metadata, daily_trends, and team_analysis")
        
        return structure_patterns
        
    finally:
        db.close()

if __name__ == "__main__":
    analyze_multiple_analyses()