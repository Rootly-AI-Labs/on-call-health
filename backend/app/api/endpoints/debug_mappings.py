"""
Debug endpoints for fixing mapping issues.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ...models import get_db
from ...models.user_mapping import UserMapping
from ...auth.dependencies import get_current_user

router = APIRouter()

@router.get("/debug/mappings/null-platforms")
async def check_null_platforms(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check for mappings with NULL source_platform."""
    
    # Count NULL mappings
    null_count = db.query(UserMapping).filter(UserMapping.source_platform.is_(None)).count()
    total_count = db.query(UserMapping).count()
    
    # Get samples
    null_samples = db.query(UserMapping).filter(
        UserMapping.source_platform.is_(None)
    ).limit(10).all()
    
    return {
        "null_count": null_count,
        "total_count": total_count,
        "samples": [
            {
                "id": m.id,
                "source_platform": m.source_platform,
                "source_identifier": m.source_identifier,
                "target_platform": m.target_platform,
                "target_identifier": m.target_identifier
            }
            for m in null_samples
        ]
    }

@router.post("/debug/mappings/fix-null-platforms")
async def fix_null_platforms(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fix mappings with NULL source_platform by setting them to 'rootly'."""
    
    try:
        # Count before
        null_count_before = db.query(UserMapping).filter(UserMapping.source_platform.is_(None)).count()
        
        if null_count_before == 0:
            return {"message": "No mappings need fixing", "updated": 0}
        
        # Update all NULL source_platform to 'rootly'
        updated_count = db.query(UserMapping).filter(
            UserMapping.source_platform.is_(None)
        ).update({
            "source_platform": "rootly"
        })
        
        db.commit()
        
        # Count after
        null_count_after = db.query(UserMapping).filter(UserMapping.source_platform.is_(None)).count()
        
        return {
            "message": "Successfully fixed mappings",
            "null_count_before": null_count_before,
            "updated_count": updated_count,
            "null_count_after": null_count_after,
            "success": True
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to fix mappings: {str(e)}")