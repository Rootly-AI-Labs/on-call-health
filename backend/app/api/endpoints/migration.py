"""
Migration endpoints for database updates
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...models import get_db, User
from ...auth.dependencies import get_current_active_user

router = APIRouter()

@router.post("/add-uuid-column")
async def migrate_add_uuid_column(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Add UUID column and populate existing analyses
    DANGER: This modifies the database structure!
    """
    
    # Only allow admin users (you can modify this check)
    if not current_user.email or "spencercheng" not in current_user.email:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # Check current state
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='analyses' AND column_name='uuid'
        """))
        uuid_exists = result.fetchone() is not None
        
        # Count analyses
        result = db.execute(text("SELECT COUNT(*) FROM analyses"))
        total_analyses = result.fetchone()[0]
        
        status = {
            "uuid_column_exists": uuid_exists,
            "total_analyses": total_analyses,
            "steps_completed": []
        }
        
        # Add column if needed
        if not uuid_exists:
            db.execute(text("ALTER TABLE analyses ADD COLUMN uuid VARCHAR(36)"))
            status["steps_completed"].append("Added UUID column")
        
        # Count analyses without UUIDs
        result = db.execute(text("SELECT COUNT(*) FROM analyses WHERE uuid IS NULL"))
        missing_uuids = result.fetchone()[0]
        status["analyses_needing_uuid"] = missing_uuids
        
        if missing_uuids > 0:
            # Get analyses without UUIDs
            result = db.execute(text("SELECT id FROM analyses WHERE uuid IS NULL"))
            analysis_ids = result.fetchall()
            
            # Populate UUIDs
            for (analysis_id,) in analysis_ids:
                new_uuid = str(uuid.uuid4())
                db.execute(text("UPDATE analyses SET uuid = :uuid WHERE id = :id"), 
                          {"uuid": new_uuid, "id": analysis_id})
            
            status["steps_completed"].append(f"Populated {len(analysis_ids)} UUIDs")
        
        # Add constraints
        try:
            db.execute(text("ALTER TABLE analyses ALTER COLUMN uuid SET NOT NULL"))
            status["steps_completed"].append("Set UUID column to NOT NULL")
        except Exception as e:
            if "not-null constraint" not in str(e).lower():
                status["warnings"] = [f"Could not set NOT NULL: {e}"]
        
        try:
            db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_analyses_uuid ON analyses(uuid)"))
            status["steps_completed"].append("Created unique index on UUID")
        except Exception as e:
            if "already exists" not in str(e).lower():
                status["warnings"] = status.get("warnings", []) + [f"Index creation issue: {e}"]
        
        # Commit changes
        db.commit()
        
        # Final verification
        result = db.execute(text("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL"))
        final_count = result.fetchone()[0]
        
        status["final_verification"] = {
            "analyses_with_uuid": final_count,
            "success": final_count == total_analyses
        }
        
        return {
            "message": "Migration completed",
            "status": status
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.get("/check-uuid-status")
async def check_uuid_status(
    db: Session = Depends(get_db)
):
    """Check current UUID migration status"""
    
    try:
        # Check if uuid column exists
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='analyses' AND column_name='uuid'
        """))
        uuid_exists = result.fetchone() is not None
        
        # Count analyses
        result = db.execute(text("SELECT COUNT(*) FROM analyses"))
        total_analyses = result.fetchone()[0]
        
        analyses_with_uuid = 0
        if uuid_exists:
            result = db.execute(text("SELECT COUNT(*) FROM analyses WHERE uuid IS NOT NULL"))
            analyses_with_uuid = result.fetchone()[0]
        
        return {
            "uuid_column_exists": uuid_exists,
            "total_analyses": total_analyses,
            "analyses_with_uuid": analyses_with_uuid,
            "migration_needed": not uuid_exists or analyses_with_uuid < total_analyses,
            "migration_complete": uuid_exists and analyses_with_uuid == total_analyses
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")