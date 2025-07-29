"""
API endpoints for integration mapping data.
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...models import get_db, IntegrationMapping
from ...auth.dependencies import get_current_active_user
from ...models.user import User
from ...services.mapping_recorder import MappingRecorder

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/mappings", summary="Get user's integration mappings")
async def get_user_mappings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get all integration mappings for the current user."""
    try:
        recorder = MappingRecorder(db)
        mappings = recorder.get_user_mappings(current_user.id)
        return [mapping.to_dict() for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching user mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mappings")

@router.get("/mappings/recent", summary="Get recent integration mappings")
async def get_recent_mappings(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get recent integration mappings for the current user."""
    try:
        recorder = MappingRecorder(db)
        mappings = recorder.get_recent_mappings(current_user.id, limit)
        return [mapping.to_dict() for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching recent mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent mappings")

@router.get("/mappings/statistics", summary="Get mapping statistics")
async def get_mapping_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get mapping statistics for the current user."""
    try:
        recorder = MappingRecorder(db)
        stats = recorder.get_mapping_statistics(current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching mapping statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mapping statistics")

@router.get("/mappings/analysis/{analysis_id}", summary="Get mappings for specific analysis")
async def get_analysis_mappings(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get all integration mappings for a specific analysis."""
    try:
        # Verify the analysis belongs to the current user
        from ...models import Analysis
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        recorder = MappingRecorder(db)
        mappings = recorder.get_analysis_mappings(analysis_id)
        return [mapping.to_dict() for mapping in mappings]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analysis mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis mappings")

@router.get("/mappings/platform/{platform}", summary="Get mappings for specific platform")
async def get_platform_mappings(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get all integration mappings for a specific target platform."""
    try:
        mappings = db.query(IntegrationMapping).filter(
            IntegrationMapping.user_id == current_user.id,
            IntegrationMapping.target_platform == platform
        ).order_by(IntegrationMapping.created_at.desc()).all()
        
        return [mapping.to_dict() for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching platform mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch platform mappings")

@router.get("/mappings/success-rate", summary="Get success rates by platform")
async def get_success_rates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get success rates broken down by platform combinations."""
    try:
        recorder = MappingRecorder(db)
        stats = recorder.get_mapping_statistics(current_user.id)
        
        # Extract just the platform stats for easier consumption
        platform_success_rates = {}
        for platform_combo, stats_data in stats.get("platform_stats", {}).items():
            platform_success_rates[platform_combo] = {
                "total_attempts": stats_data["total"],
                "successful": stats_data["successful"],
                "failed": stats_data["failed"],
                "success_rate": round(stats_data["success_rate"] * 100, 1)  # Convert to percentage
            }
        
        return {
            "overall_success_rate": round(stats.get("success_rate", 0) * 100, 1),
            "total_attempts": stats.get("total_attempts", 0),
            "platform_breakdown": platform_success_rates
        }
    except Exception as e:
        logger.error(f"Error fetching success rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch success rates")