"""
Admin endpoints for database maintenance and fixes.
"""
import os
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...models import Analysis
from ...core.rootly_client import RootlyAPIClient
from ...core.pagerduty_client import PagerDutyAPIClient

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

@router.post("/fix-null-organizations")
async def fix_null_organizations(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Fix historical analyses that have null organization names.
    This is a one-time maintenance endpoint.
    """
    
    # Get beta tokens for API calls
    beta_rootly_token = os.getenv('ROOTLY_API_TOKEN')
    beta_pagerduty_token = os.getenv('PAGERDUTY_API_TOKEN')
    
    # Get real organization names from APIs
    rootly_org_name = None
    pagerduty_org_name = None
    
    try:
        if beta_rootly_token:
            rootly_client = RootlyAPIClient(beta_rootly_token)
            rootly_result = await rootly_client.test_connection()
            if rootly_result.get("status") == "success":
                account_info = rootly_result.get("account_info", {})
                rootly_org_name = account_info.get("organization_name")
    except Exception as e:
        print(f"Failed to get Rootly org name: {e}")
        
    try:
        if beta_pagerduty_token:
            pagerduty_client = PagerDutyAPIClient(beta_pagerduty_token)
            pagerduty_result = await pagerduty_client.test_connection()
            if pagerduty_result.get("valid"):
                account_info = pagerduty_result.get("account_info", {})
                pagerduty_org_name = account_info.get("organization_name")
    except Exception as e:
        print(f"Failed to get PagerDuty org name: {e}")
    
    # Find and fix analyses with null organization names
    analyses = db.query(Analysis).filter(
        Analysis.results.isnot(None)
    ).all()
    
    updated_count = 0
    analysis_details = []
    
    for analysis in analyses:
        if analysis.results and isinstance(analysis.results, dict):
            metadata = analysis.results.get('metadata', {})
            
            # Check if organization_name is null or missing
            current_org_name = metadata.get('organization_name')
            if current_org_name is None or current_org_name == 'null':
                # Determine new organization name
                config = analysis.config or {}
                beta_integration_id = config.get('beta_integration_id')
                
                new_org_name = None
                if beta_integration_id == "beta-rootly" and rootly_org_name:
                    new_org_name = rootly_org_name
                elif beta_integration_id == "beta-pagerduty" and pagerduty_org_name:
                    new_org_name = pagerduty_org_name
                else:
                    # Generic fallback
                    new_org_name = "Organization"
                
                # Update the organization name
                metadata['organization_name'] = new_org_name
                analysis.results['metadata'] = metadata
                
                # Mark as modified
                db.add(analysis)
                updated_count += 1
                
                analysis_details.append({
                    "id": analysis.id,
                    "created_at": analysis.created_at.isoformat(),
                    "old_name": current_org_name,
                    "new_name": new_org_name,
                    "beta_integration": beta_integration_id
                })
    
    if updated_count > 0:
        db.commit()
    
    # Get summary of organization names after update
    org_summary = {}
    total_analyses = 0
    
    for analysis in analyses:
        if analysis.results and isinstance(analysis.results, dict):
            metadata = analysis.results.get('metadata', {})
            org_name = metadata.get('organization_name', 'Unknown')
            org_summary[org_name] = org_summary.get(org_name, 0) + 1
            total_analyses += 1
    
    return {
        "status": "success",
        "updated_count": updated_count,
        "total_analyses": total_analyses,
        "organization_summary": org_summary,
        "api_org_names": {
            "rootly": rootly_org_name,
            "pagerduty": pagerduty_org_name
        },
        "updated_analyses": analysis_details[:10],  # Show first 10 for brevity
        "message": f"Updated {updated_count} analyses with proper organization names"
    }