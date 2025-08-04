"""
API endpoints for manual mapping management.
"""
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

from ...models import get_db, UserMapping
from ...auth.dependencies import get_current_active_user
from ...models.user import User
from ...services.manual_mapping_service import ManualMappingService

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response
class CreateMappingRequest(BaseModel):
    source_platform: str = Field(..., description="Source platform (rootly, pagerduty)")
    source_identifier: str = Field(..., description="Source identifier (email, name)")
    target_platform: str = Field(..., description="Target platform (github, slack)")
    target_identifier: str = Field(..., description="Target identifier (username, user_id)")
    mapping_type: str = Field(default="manual", description="Type of mapping")

class UpdateMappingRequest(BaseModel):
    target_identifier: str = Field(..., description="New target identifier")

class BulkMappingRequest(BaseModel):
    mappings: List[CreateMappingRequest] = Field(..., description="List of mappings to create")

class MappingValidationRequest(BaseModel):
    target_platform: str = Field(..., description="Target platform to validate")
    target_identifier: str = Field(..., description="Target identifier to validate")

class MappingResponse(BaseModel):
    id: int
    source_platform: str
    source_identifier: str
    target_platform: str
    target_identifier: str
    mapping_type: str
    confidence_score: Optional[float]
    last_verified: Optional[str]
    created_at: str
    updated_at: Optional[str]
    status: str
    is_verified: bool
    mapping_key: str

class MappingStatisticsResponse(BaseModel):
    total_mappings: int
    manual_mappings: int
    auto_detected_mappings: int
    verified_mappings: int
    verification_rate: float
    platform_breakdown: Dict[str, Dict[str, int]]
    last_updated: Optional[str]

class SuggestionResponse(BaseModel):
    target_identifier: str
    confidence: float
    evidence: List[str]
    method: str

@router.get("/manual-mappings", summary="Get all manual mappings for current user")
async def get_user_mappings(
    target_platform: Optional[str] = Query(None, description="Filter by target platform"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[MappingResponse]:
    """Get all manual mappings for the current user."""
    try:
        service = ManualMappingService(db)
        
        if target_platform:
            mappings = service.get_platform_mappings(current_user.id, target_platform)
        else:
            mappings = service.get_user_mappings(current_user.id)
        
        return [MappingResponse(**mapping.to_dict()) for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching user mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mappings")

@router.post("/manual-mappings", summary="Create a new manual mapping")
async def create_mapping(
    request: CreateMappingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MappingResponse:
    """Create a new manual mapping."""
    try:
        service = ManualMappingService(db)
        
        mapping = service.create_mapping(
            user_id=current_user.id,
            source_platform=request.source_platform,
            source_identifier=request.source_identifier,
            target_platform=request.target_platform,
            target_identifier=request.target_identifier,
            created_by=current_user.id,
            mapping_type=request.mapping_type
        )
        
        return MappingResponse(**mapping.to_dict())
    except Exception as e:
        logger.error(f"Error creating mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to create mapping")

@router.put("/manual-mappings/{mapping_id}", summary="Update an existing mapping")
async def update_mapping(
    mapping_id: int,
    request: UpdateMappingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MappingResponse:
    """Update an existing mapping."""
    try:
        # Get existing mapping
        mapping = db.query(UserMapping).filter(
            UserMapping.id == mapping_id,
            UserMapping.user_id == current_user.id
        ).first()
        
        if not mapping:
            raise HTTPException(status_code=404, detail="Mapping not found")
        
        # Update mapping
        mapping.target_identifier = request.target_identifier
        mapping.updated_at = func.now()
        mapping.last_verified = func.now()  # Reset verification on update
        
        db.commit()
        db.refresh(mapping)
        
        return MappingResponse(**mapping.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to update mapping")

@router.delete("/manual-mappings/{mapping_id}", summary="Delete a mapping")
async def delete_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a mapping."""
    try:
        service = ManualMappingService(db)
        
        if service.delete_mapping(mapping_id, current_user.id):
            return {"message": "Mapping deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Mapping not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete mapping")

@router.post("/manual-mappings/{mapping_id}/verify", summary="Verify a mapping")
async def verify_mapping(
    mapping_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Mark a mapping as verified."""
    try:
        service = ManualMappingService(db)
        
        if service.verify_mapping(mapping_id, current_user.id):
            return {"message": "Mapping verified successfully"}
        else:
            raise HTTPException(status_code=404, detail="Mapping not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify mapping")

@router.post("/manual-mappings/bulk", summary="Bulk create mappings")
async def bulk_create_mappings(
    request: BulkMappingRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Bulk create multiple mappings."""
    try:
        service = ManualMappingService(db)
        
        mappings_data = [mapping.dict() for mapping in request.mappings]
        created_mappings, errors = service.bulk_create_mappings(
            user_id=current_user.id,
            mappings_data=mappings_data,
            created_by=current_user.id
        )
        
        return {
            "created_count": len(created_mappings),
            "error_count": len(errors),
            "mappings": [MappingResponse(**mapping.to_dict()) for mapping in created_mappings],
            "errors": errors
        }
    except Exception as e:
        logger.error(f"Error bulk creating mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to bulk create mappings")

@router.get("/manual-mappings/statistics", summary="Get mapping statistics")
async def get_mapping_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> MappingStatisticsResponse:
    """Get mapping statistics for the current user."""
    try:
        service = ManualMappingService(db)
        stats = service.get_mapping_statistics(current_user.id)
        
        # Convert datetime to string
        if stats["last_updated"]:
            stats["last_updated"] = stats["last_updated"].isoformat()
        
        return MappingStatisticsResponse(**stats)
    except Exception as e:
        logger.error(f"Error fetching mapping statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch statistics")

@router.get("/manual-mappings/suggestions", summary="Get mapping suggestions")
async def get_mapping_suggestions(
    source_platform: str = Query(..., description="Source platform"),
    source_identifier: str = Query(..., description="Source identifier"),
    target_platform: str = Query(..., description="Target platform"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[SuggestionResponse]:
    """Get mapping suggestions based on existing patterns."""
    try:
        service = ManualMappingService(db)
        suggestions = service.suggest_mappings(
            user_id=current_user.id,
            source_platform=source_platform,
            source_identifier=source_identifier,
            target_platform=target_platform
        )
        
        return [SuggestionResponse(**suggestion) for suggestion in suggestions]
    except Exception as e:
        logger.error(f"Error fetching mapping suggestions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch suggestions")

@router.post("/manual-mappings/validate", summary="Validate a mapping")
async def validate_mapping(
    request: MappingValidationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Validate if a target identifier exists and is active."""
    try:
        # For now, return a basic validation
        # TODO: Implement actual validation against GitHub/Slack APIs
        validation_result = {
            "valid": True,  # Placeholder
            "exists": True,  # Placeholder
            "platform": request.target_platform,
            "identifier": request.target_identifier,
            "last_activity": None,  # Would check API for last activity
            "activity_score": 0.8,  # Placeholder confidence score
            "message": "Validation not yet implemented - assuming valid"
        }
        
        return validation_result
    except Exception as e:
        logger.error(f"Error validating mapping: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate mapping")

@router.get("/manual-mappings/unmapped", summary="Get unmapped identifiers")
async def get_unmapped_identifiers(
    source_platform: str = Query(..., description="Source platform"),
    target_platform: str = Query(..., description="Target platform"),
    source_identifiers: str = Query(..., description="Comma-separated source identifiers"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get source identifiers that don't have mappings to target platform."""
    try:
        service = ManualMappingService(db)
        identifier_list = [id.strip() for id in source_identifiers.split(",")]
        
        unmapped = service.get_unmapped_identifiers(
            user_id=current_user.id,
            source_platform=source_platform,
            source_identifiers=identifier_list,
            target_platform=target_platform
        )
        
        return {
            "unmapped_identifiers": unmapped,
            "total_checked": len(identifier_list),
            "unmapped_count": len(unmapped),
            "mapping_coverage": (len(identifier_list) - len(unmapped)) / len(identifier_list) if identifier_list else 0
        }
    except Exception as e:
        logger.error(f"Error fetching unmapped identifiers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch unmapped identifiers")

@router.post("/manual-mappings/run-github-mapping", summary="Run GitHub mapping process")
async def run_github_mapping(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run the enhanced GitHub mapping process for all unmapped users."""
    try:
        from ...services.enhanced_github_matcher import EnhancedGitHubMatcher
        from ...models import Integration
        import asyncio
        
        # Get GitHub integration
        github_integration = db.query(Integration).filter(
            Integration.user_id == current_user.id,
            Integration.platform == "github",
            Integration.github_token.isnot(None)
        ).first()
        
        if not github_integration:
            raise HTTPException(status_code=400, detail="GitHub integration not found")
        
        # Decrypt GitHub token
        from ..github import decrypt_token
        github_token = decrypt_token(github_integration.github_token)
        
        # Get unmapped Rootly users
        service = ManualMappingService(db)
        
        # Get all Rootly/PagerDuty users
        rootly_integrations = db.query(Integration).filter(
            Integration.user_id == current_user.id,
            Integration.platform.in_(["rootly", "pagerduty"])
        ).all()
        
        all_users = []
        for integration in rootly_integrations:
            # Get users from this integration
            if integration.platform == "rootly":
                from ...core.rootly_client import RootlyAPIClient
                client = RootlyAPIClient(integration.api_token)
                users_data = await client.get_users()
                for user in users_data:
                    all_users.append({
                        "email": user.get("email"),
                        "name": user.get("full_name") or user.get("name"),
                        "platform": "rootly",
                        "integration_id": integration.id
                    })
            # TODO: Add PagerDuty support
        
        # Get existing mappings
        existing_mappings = service.get_all_mappings(
            user_id=current_user.id,
            target_platform="github"
        )
        mapped_emails = {m.source_identifier for m in existing_mappings if m.source_platform == "rootly"}
        
        # Filter unmapped users
        unmapped_users = [u for u in all_users if u["email"] not in mapped_emails]
        
        # Get GitHub organizations from integration settings
        github_orgs = []
        if hasattr(github_integration, 'github_organizations') and github_integration.github_organizations:
            import json
            try:
                github_orgs = json.loads(github_integration.github_organizations)
            except:
                github_orgs = ["rootly-hq"]  # Default fallback
        
        if not github_orgs:
            github_orgs = ["rootly-hq"]  # Default if not configured
            
        # Run matching process
        matcher = EnhancedGitHubMatcher(github_token, github_orgs)
        results = []
        
        for i, user in enumerate(unmapped_users):
            try:
                # Send progress update via SSE or WebSocket (future enhancement)
                github_username = await matcher.match_email_to_github(
                    email=user["email"],
                    full_name=user["name"]
                )
                
                if github_username:
                    # Create mapping
                    service.create_mapping(
                        user_id=current_user.id,
                        source_platform=user["platform"],
                        source_identifier=user["email"],
                        target_platform="github",
                        target_identifier=github_username,
                        mapping_type="automated"
                    )
                    
                    results.append({
                        "email": user["email"],
                        "name": user["name"],
                        "github_username": github_username,
                        "status": "mapped",
                        "platform": user["platform"]
                    })
                else:
                    results.append({
                        "email": user["email"],
                        "name": user["name"],
                        "github_username": None,
                        "status": "not_found",
                        "platform": user["platform"]
                    })
                    
            except Exception as e:
                logger.error(f"Error mapping {user['email']}: {e}")
                results.append({
                    "email": user["email"],
                    "name": user["name"],
                    "github_username": None,
                    "status": "error",
                    "error": str(e),
                    "platform": user["platform"]
                })
        
        # Calculate summary stats
        mapped_count = len([r for r in results if r["status"] == "mapped"])
        not_found_count = len([r for r in results if r["status"] == "not_found"])
        error_count = len([r for r in results if r["status"] == "error"])
        
        return {
            "total_processed": len(results),
            "mapped": mapped_count,
            "not_found": not_found_count,
            "errors": error_count,
            "success_rate": mapped_count / len(results) if results else 0,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running GitHub mapping: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to run GitHub mapping: {str(e)}")