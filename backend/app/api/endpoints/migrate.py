"""
Database migration endpoints - for running migrations via API
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ...models import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/add-integration-fields")
async def add_integration_fields_migration(db: Session = Depends(get_db)):
    """
    Add integration_name and platform fields to analyses table
    
    This can be called via API instead of running migration script directly
    """
    try:
        logger.info("🔧 Starting migration: Add integration_name and platform columns...")
        
        # Check if columns already exist
        existing_columns = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'analyses' 
            AND column_name IN ('integration_name', 'platform')
        """))
        
        existing = [row[0] for row in existing_columns.fetchall()]
        
        if 'integration_name' in existing and 'platform' in existing:
            return {
                "success": True,
                "message": "✅ Columns already exist - migration not needed",
                "existing_columns": existing
            }
        
        # Add the new columns
        if 'integration_name' not in existing:
            db.execute(text("ALTER TABLE analyses ADD COLUMN integration_name VARCHAR(255)"))
            logger.info("✅ Added integration_name column")
        
        if 'platform' not in existing:
            db.execute(text("ALTER TABLE analyses ADD COLUMN platform VARCHAR(50)"))
            logger.info("✅ Added platform column")
        
        db.commit()
        
        # Verify the columns were added
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'analyses' 
            AND column_name IN ('integration_name', 'platform')
            ORDER BY column_name
        """))
        
        columns = [dict(row._mapping) for row in result.fetchall()]
        
        # Check total analyses
        count_result = db.execute(text("SELECT COUNT(*) as count FROM analyses"))
        total_analyses = count_result.fetchone()[0]
        
        logger.info("🎉 Migration completed successfully!")
        
        return {
            "success": True,
            "message": "🎉 Migration completed successfully!",
            "columns_added": columns,
            "total_analyses": total_analyses,
            "note": "New analyses will populate these fields automatically"
        }
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.get("/check-integration-fields")
async def check_integration_fields(db: Session = Depends(get_db)):
    """Check if migration has been run"""
    try:
        # Check if columns exist
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'analyses' 
            AND column_name IN ('integration_name', 'platform')
            ORDER BY column_name
        """))
        
        columns = [dict(row._mapping) for row in result.fetchall()]
        
        # Count analyses
        count_result = db.execute(text("SELECT COUNT(*) as count FROM analyses"))
        total_analyses = count_result.fetchone()[0]
        
        # Count analyses with new fields populated
        populated_result = db.execute(text("""
            SELECT COUNT(*) as count 
            FROM analyses 
            WHERE integration_name IS NOT NULL AND platform IS NOT NULL
        """))
        populated_analyses = populated_result.fetchone()[0]
        
        migration_needed = len(columns) < 2
        
        return {
            "migration_needed": migration_needed,
            "columns_exist": columns,
            "total_analyses": total_analyses,
            "analyses_with_new_fields": populated_analyses,
            "message": "Migration needed - columns missing" if migration_needed else "✅ Migration completed"
        }
        
    except Exception as e:
        logger.error(f"Error checking migration status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Check failed: {str(e)}")