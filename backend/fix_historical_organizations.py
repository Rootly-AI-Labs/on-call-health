#!/usr/bin/env python3
"""
Enhanced script to fix null organization names in existing analyses.
This version determines better organization names based on analysis data.
"""

import os
import sys
import asyncio
from datetime import datetime
from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import sessionmaker

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

try:
    from app.models import Analysis
    from app.core.database import get_db
    from app.core.rootly_client import RootlyAPIClient
    from app.core.pagerduty_client import PagerDutyAPIClient
except ImportError:
    # Fallback imports
    from models import Analysis

async def get_real_organization_name(platform: str, api_token: str) -> str:
    """Get real organization name from API."""
    try:
        if platform == "rootly":
            client = RootlyAPIClient(api_token)
            result = await client.test_connection()
            account_info = result.get("account_info", {})
            org_name = account_info.get("organization_name")
            if org_name:
                return org_name
        elif platform == "pagerduty":
            client = PagerDutyAPIClient(api_token)
            result = await client.test_connection()
            if result.get("valid"):
                account_info = result.get("account_info", {})
                org_name = account_info.get("organization_name")
                if org_name:
                    return org_name
    except Exception as e:
        print(f"Failed to get org name from {platform} API: {e}")
    
    return None

async def fix_historical_organizations():
    """Update analyses with null organization names using real API data."""
    
    # Use DATABASE_URL from environment or default
    database_url = os.getenv('DATABASE_URL', 'postgresql://localhost/burnout_detector')
    
    print(f"Connecting to database: {database_url[:50]}...")
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Get beta tokens for API calls
    beta_rootly_token = os.getenv('ROOTLY_API_TOKEN')
    beta_pagerduty_token = os.getenv('PAGERDUTY_API_TOKEN')
    
    # Get real organization names
    rootly_org_name = None
    pagerduty_org_name = None
    
    if beta_rootly_token:
        print("Fetching real Rootly organization name...")
        rootly_org_name = await get_real_organization_name("rootly", beta_rootly_token)
        print(f"Rootly organization: {rootly_org_name or 'Unable to fetch'}")
        
    if beta_pagerduty_token:
        print("Fetching real PagerDuty organization name...")  
        pagerduty_org_name = await get_real_organization_name("pagerduty", beta_pagerduty_token)
        print(f"PagerDuty organization: {pagerduty_org_name or 'Unable to fetch'}")
    
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
                current_org_name = metadata.get('organization_name')
                if current_org_name is None or current_org_name == 'null':
                    # Try to determine organization name from analysis config
                    config = analysis.config or {}
                    beta_integration_id = config.get('beta_integration_id')
                    
                    new_org_name = None
                    if beta_integration_id == "beta-rootly" and rootly_org_name:
                        new_org_name = rootly_org_name
                    elif beta_integration_id == "beta-pagerduty" and pagerduty_org_name:
                        new_org_name = pagerduty_org_name
                    else:
                        # Fallback to generic but better than null
                        new_org_name = "Organization"
                    
                    print(f"Fixing analysis {analysis.id} ({analysis.created_at.strftime('%Y-%m-%d %H:%M')}) - setting organization to '{new_org_name}'")
                    
                    # Update the organization name in the results
                    metadata['organization_name'] = new_org_name
                    analysis.results['metadata'] = metadata
                    
                    # Mark as modified
                    db.add(analysis)
                    updated_count += 1
        
        if updated_count > 0:
            db.commit()
            print(f"✅ Updated {updated_count} analyses with proper organization names")
        else:
            print("ℹ️  No analyses needed updating")
        
        # Show summary of what we now have
        print("\n📊 Organization name summary after update:")
        org_counts = {}
        total_analyses = 0
        
        for analysis in analyses:
            if analysis.results and isinstance(analysis.results, dict):
                metadata = analysis.results.get('metadata', {})
                org_name = metadata.get('organization_name', 'Unknown')
                org_counts[org_name] = org_counts.get(org_name, 0) + 1
                total_analyses += 1
        
        for org_name, count in sorted(org_counts.items()):
            print(f"  {org_name}: {count} analyses")
        print(f"  Total: {total_analyses} analyses")

if __name__ == "__main__":
    asyncio.run(fix_historical_organizations())