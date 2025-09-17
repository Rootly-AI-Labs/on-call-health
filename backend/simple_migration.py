#!/usr/bin/env python3
"""
Simple migration runner for Docker environment
Adds integration_name and platform columns to analyses table
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Try Railway environment variable
        database_url = os.getenv('RAILWAY_DATABASE_URL')
    if not database_url:
        # Try common postgres format
        host = os.getenv('PGHOST', 'localhost')
        port = os.getenv('PGPORT', '5432')
        user = os.getenv('PGUSER', 'postgres')
        password = os.getenv('PGPASSWORD', '')
        database = os.getenv('PGDATABASE', 'burnout_detector')
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"

    logger.info(f"🔗 Using database URL: {database_url[:50]}...")
    return database_url

def run_migration():
    """Run the integration fields migration"""

    try:
        database_url = get_database_url()
        engine = create_engine(database_url)

        with engine.connect() as conn:
            logger.info("🔧 Adding integration_name and platform columns to analyses table...")

            # Create migrations tracking table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS migrations (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'completed'
                )
            """))

            # Check if migration already applied
            result = conn.execute(text("""
                SELECT COUNT(*) as count FROM migrations
                WHERE name = '001_add_integration_fields_to_analyses'
                AND status = 'completed'
            """))

            if result.fetchone()[0] > 0:
                logger.info("⏭️  Migration already applied, skipping...")
                return True

            # Add the columns
            conn.execute(text("""
                ALTER TABLE analyses
                ADD COLUMN IF NOT EXISTS integration_name VARCHAR(255),
                ADD COLUMN IF NOT EXISTS platform VARCHAR(50)
            """))

            # Mark migration as applied
            conn.execute(text("""
                INSERT INTO migrations (name, status)
                VALUES ('001_add_integration_fields_to_analyses', 'completed')
                ON CONFLICT (name) DO UPDATE SET
                    applied_at = CURRENT_TIMESTAMP,
                    status = 'completed'
            """))

            conn.commit()

            logger.info("✅ Successfully added integration_name and platform columns")

            # Verify the columns were added
            result = conn.execute(text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'analyses'
                AND column_name IN ('integration_name', 'platform')
                ORDER BY column_name
            """))

            columns = result.fetchall()
            logger.info(f"📊 Verified new columns: {[dict(row._mapping) for row in columns]}")

            return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Simple migration runner starting...")
    success = run_migration()

    if success:
        logger.info("🎉 Migration completed successfully!")
    else:
        logger.error("❌ Migration failed")
        sys.exit(1)

    sys.exit(0)