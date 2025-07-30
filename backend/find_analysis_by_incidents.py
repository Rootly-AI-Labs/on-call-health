#!/usr/bin/env python3
"""
Find analyses by incident count.
"""
import os
import sys
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

def find_analyses_by_incident_count(target_count=273):
    """Find analyses with incident counts close to the target."""
    db = connect_to_database()
    
    try:
        # Query all completed analyses with results
        analyses = db.query(Analysis).filter(
            Analysis.status == 'completed',
            Analysis.results.isnot(None)
        ).order_by(Analysis.id.desc()).all()
        
        if not analyses:
            print("No completed analyses with results found!")
            return
        
        candidates = []
        
        print(f"Searching for analyses with incident counts close to {target_count}...")
        print()
        print(f"ID | UUID | Time Range | Total Incidents | Difference from {target_count}")
        print("-" * 70)
        
        for analysis in analyses:
            if analysis.results:
                metadata = analysis.results.get('metadata', {})
                total_incidents = metadata.get('total_incidents', 0)
                
                if isinstance(total_incidents, (int, float)):
                    difference = abs(total_incidents - target_count)
                    
                    # Show analyses within 50 incidents of target
                    if difference <= 50 or total_incidents == target_count:
                        uuid_str = str(analysis.uuid)[:8] + "..." if analysis.uuid else "None"
                        print(f"{analysis.id:2d} | {uuid_str:12s} | {analysis.time_range:10d} | {total_incidents:15d} | {difference:4d}")
                        
                        candidates.append({
                            'id': analysis.id,
                            'uuid': analysis.uuid,
                            'incidents': total_incidents,
                            'difference': difference,
                            'time_range': analysis.time_range
                        })
        
        # Sort by closest to target
        candidates.sort(key=lambda x: x['difference'])
        
        if candidates:
            print()
            print(f"Best candidates (closest to {target_count} incidents):")
            for i, candidate in enumerate(candidates[:5]):
                print(f"  {i+1}. ID {candidate['id']}: {candidate['incidents']} incidents (diff: {candidate['difference']})")
                
            # Return the best candidate for detailed analysis
            return candidates[0]['id']
        else:
            print(f"No analyses found with incident counts close to {target_count}")
            
            # Show some high-incident analyses instead
            print()
            print("High-incident analyses that might be of interest:")
            high_incident_analyses = []
            
            for analysis in analyses:
                if analysis.results:
                    metadata = analysis.results.get('metadata', {})
                    total_incidents = metadata.get('total_incidents', 0)
                    
                    if isinstance(total_incidents, (int, float)) and total_incidents > 100:
                        high_incident_analyses.append({
                            'id': analysis.id,
                            'incidents': total_incidents,
                            'time_range': analysis.time_range
                        })
            
            # Sort by incident count descending
            high_incident_analyses.sort(key=lambda x: x['incidents'], reverse=True)
            
            for analysis in high_incident_analyses[:10]:
                print(f"  ID {analysis['id']}: {analysis['incidents']} incidents ({analysis['time_range']} days)")
                
            return high_incident_analyses[0]['id'] if high_incident_analyses else None
    
    finally:
        db.close()

if __name__ == "__main__":
    target = 273
    if len(sys.argv) > 1:
        target = int(sys.argv[1])
    
    best_id = find_analyses_by_incident_count(target)
    if best_id:
        print(f"\nSuggestion: Run audit on analysis ID {best_id}")