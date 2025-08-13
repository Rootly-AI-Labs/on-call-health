#!/usr/bin/env python3
"""
One-time script to fix null organization names in existing analyses.
Run this once to update historical analyses.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from models import Analysis

def fix_null_organizations():
    """Update analyses with null organization names to show 'Beta Organization'."""
    
    # Use DATABASE_URL from environment or default
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./burnout_detector.db')
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        # Find analyses with null organization names in results metadata
        analyses = db.query(Analysis).filter(
            Analysis.results.isnot(None)
        ).all()
        
        updated_count = 0
        
        for analysis in analyses:
            if analysis.results and isinstance(analysis.results, dict):
                metadata = analysis.results.get('metadata', {})
                
                # Check if organization_name is null or missing
                if metadata.get('organization_name') is None:
                    print(f"Fixing analysis {analysis.id} - setting organization name to 'Beta Organization'")
                    
                    # Update the organization name in the results
                    metadata['organization_name'] = 'Beta Organization'
                    analysis.results['metadata'] = metadata
                    
                    # Mark as modified
                    db.add(analysis)
                    updated_count += 1
        
        if updated_count > 0:
            db.commit()
            print(f"✅ Updated {updated_count} analyses with proper organization names")
        else:
            print("ℹ️  No analyses needed updating")

if __name__ == "__main__":
    fix_null_organizations()