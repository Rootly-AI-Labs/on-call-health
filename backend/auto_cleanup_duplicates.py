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
            # Check for duplicates across all platforms
            check_query = text("""
            SELECT target_platform, COUNT(*) as duplicate_groups
            FROM (
                SELECT user_id, source_identifier, target_platform, COUNT(*) as cnt
                FROM integration_mappings 
                WHERE target_platform IN ('github', 'slack')
                GROUP BY user_id, source_identifier, target_platform 
                HAVING COUNT(*) > 1
            ) duplicates
            GROUP BY target_platform
            """)
            
            duplicates_by_platform = db.execute(check_query).fetchall()
            
            if not duplicates_by_platform:
                logger.info("✅ No duplicate mappings found for GitHub or Slack")
                return
            
            total_deleted = 0
            
            # Clean up duplicates for each platform
            for platform, duplicate_count in duplicates_by_platform:
                logger.info(f"🧹 Found {duplicate_count} duplicate {platform} mapping groups, cleaning up...")
                
                # Clean up duplicates - keep most recent for each user-email-platform combo
                cleanup_query = text("""
                DELETE FROM integration_mappings 
                WHERE id NOT IN (
                    SELECT DISTINCT ON (user_id, source_identifier, target_platform) id
                    FROM integration_mappings 
                    WHERE target_platform = :platform
                    ORDER BY user_id, source_identifier, target_platform, created_at DESC
                )
                AND target_platform = :platform
                """)
                
                result = db.execute(cleanup_query, {"platform": platform})
                deleted_count = result.rowcount
                total_deleted += deleted_count
                
                logger.info(f"🎉 {platform} cleanup complete: Removed {deleted_count} duplicate mappings")
            
            db.commit()
            logger.info(f"🎉 Total auto-cleanup complete: Removed {total_deleted} duplicate mappings across all platforms")
            
    except Exception as e:
        logger.error(f"❌ Auto-cleanup failed: {e}")

if __name__ == "__main__":
    auto_cleanup_duplicates()