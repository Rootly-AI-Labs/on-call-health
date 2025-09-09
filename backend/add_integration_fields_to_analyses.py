#!/usr/bin/env python3
"""
Migration: Add integration_name and platform fields to analyses table

This migration adds:
- integration_name: Store the display name ("PagerDuty (Beta Access)", "Failwhale Tales", etc.)  
- platform: Store the platform type ("rootly", "pagerduty")

This eliminates the need for complex frontend matching logic.
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models import get_db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add integration_name and platform columns to analyses table"""
    
    db = next(get_db())
    
    try:
        logger.info("🔧 Adding integration_name and platform columns to analyses table...")
        
        # Add the new columns
        db.execute(text("""
            ALTER TABLE analyses 
            ADD COLUMN integration_name VARCHAR(255),
            ADD COLUMN platform VARCHAR(50)
        """))
        
        db.commit()
        logger.info("✅ Successfully added integration_name and platform columns")
        
        # Verify the columns were added
        result = db.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'analyses' 
            AND column_name IN ('integration_name', 'platform')
            ORDER BY column_name
        """))
        
        columns = result.fetchall()
        logger.info(f"📊 Verified new columns: {[dict(row._mapping) for row in columns]}")
        
        # Check how many analyses exist
        count_result = db.execute(text("SELECT COUNT(*) as count FROM analyses"))
        total_analyses = count_result.fetchone()[0]
        logger.info(f"📈 Total analyses in database: {total_analyses}")
        
        logger.info("🎉 Migration completed successfully!")
        logger.info("📝 Note: Existing analyses will have NULL values for these fields")
        logger.info("📝 New analyses will populate these fields automatically")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()