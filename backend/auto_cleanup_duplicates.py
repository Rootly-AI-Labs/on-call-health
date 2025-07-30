"""
Auto-cleanup script that runs on startup to remove duplicate mappings.
This will automatically clean up duplicates when the app starts.
"""
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)

def auto_cleanup_duplicates():
    """Automatically clean up duplicate mappings on startup."""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            logger.warning("No DATABASE_URL found, skipping duplicate cleanup")
            return
        
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        
        with SessionLocal() as db:
            # Check for duplicates
            check_query = text("""
            SELECT COUNT(*) as duplicate_groups
            FROM (
                SELECT user_id, source_identifier, COUNT(*) as cnt
                FROM integration_mappings 
                WHERE target_platform = 'github'
                GROUP BY user_id, source_identifier 
                HAVING COUNT(*) > 1
            ) duplicates
            """)
            
            duplicate_count = db.execute(check_query).fetchone()[0]
            
            if duplicate_count == 0:
                logger.info("✅ No duplicate GitHub mappings found")
                return
            
            logger.info(f"🧹 Found {duplicate_count} duplicate mapping groups, cleaning up...")
            
            # Clean up duplicates - keep most recent for each user-email combo
            cleanup_query = text("""
            DELETE FROM integration_mappings 
            WHERE id NOT IN (
                SELECT DISTINCT ON (user_id, source_identifier) id
                FROM integration_mappings 
                WHERE target_platform = 'github'
                ORDER BY user_id, source_identifier, created_at DESC
            )
            AND target_platform = 'github'
            """)
            
            result = db.execute(cleanup_query)
            deleted_count = result.rowcount
            db.commit()
            
            logger.info(f"🎉 Auto-cleanup complete: Removed {deleted_count} duplicate mappings")
            
    except Exception as e:
        logger.error(f"❌ Auto-cleanup failed: {e}")

if __name__ == "__main__":
    auto_cleanup_duplicates()