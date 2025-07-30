#!/usr/bin/env python3
"""
List all analyses in the database.
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

def list_all_analyses():
    """List all analyses in the database."""
    db = connect_to_database()
    
    try:
        # Query all analyses
        analyses = db.query(Analysis).order_by(Analysis.id.desc()).all()
        
        if not analyses:
            print("No analyses found in the database!")
            return
        
        print(f"Found {len(analyses)} analyses:")
        print()
        print("ID | UUID | Status | Time Range | Created | Completed | Has Results")
        print("-" * 80)
        
        for analysis in analyses:
            uuid_str = str(analysis.uuid)[:8] + "..." if analysis.uuid else "None"
            created_str = analysis.created_at.strftime("%Y-%m-%d %H:%M") if analysis.created_at else "None"
            completed_str = analysis.completed_at.strftime("%Y-%m-%d %H:%M") if analysis.completed_at else "None"
            has_results = "Yes" if analysis.results else "No"
            
            print(f"{analysis.id:2d} | {uuid_str:12s} | {analysis.status:10s} | {analysis.time_range:10d} | {created_str:16s} | {completed_str:16s} | {has_results}")
        
        # Show recent completed analyses with results
        completed_with_results = [a for a in analyses if a.status == 'completed' and a.results]
        if completed_with_results:
            print()
            print("Recent completed analyses with results (candidates for audit):")
            for analysis in completed_with_results[:5]:
                print(f"  ID {analysis.id}: {analysis.status}, {analysis.time_range} days, UUID: {analysis.uuid}")
                
                # Quick peek at results structure
                if analysis.results:
                    metadata = analysis.results.get('metadata', {})
                    total_incidents = metadata.get('total_incidents', 'Unknown')
                    print(f"    Total incidents: {total_incidents}")
    
    finally:
        db.close()

if __name__ == "__main__":
    list_all_analyses()