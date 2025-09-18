#!/usr/bin/env python3
"""
Migration script to create the user_burnout_reports table.

This script adds support for user self-reported burnout assessments,
enabling comparison between automated CBI scores and user perceptions.

Usage:
    python migrate_user_burnout_reports.py
"""

import os
import sys

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment variables."""
    # Try Railway/production environment variables first
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')

    # Try individual components
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DATABASE', 'burnout_detector')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

def create_user_burnout_reports_table(engine):
    """Create the user_burnout_reports table."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS user_burnout_reports (
        id SERIAL PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,

        -- Core self-reported scores (0-100 scale to match CBI)
        self_reported_score INTEGER NOT NULL CHECK (self_reported_score >= 0 AND self_reported_score <= 100),
        energy_level INTEGER NOT NULL CHECK (energy_level >= 1 AND energy_level <= 5),

        -- Stress factors as JSON array
        stress_factors JSON,

        -- Optional context
        additional_comments TEXT,

        -- Metadata
        submitted_via VARCHAR(20) DEFAULT 'web',
        is_anonymous BOOLEAN DEFAULT FALSE,
        submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

        -- Unique constraint: one report per user per analysis
        CONSTRAINT unique_user_analysis_report UNIQUE(user_id, analysis_id)
    );
    """

    create_indexes_sql = """
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_user_burnout_reports_user_id ON user_burnout_reports(user_id);
    CREATE INDEX IF NOT EXISTS idx_user_burnout_reports_analysis_id ON user_burnout_reports(analysis_id);
    CREATE INDEX IF NOT EXISTS idx_user_burnout_reports_submitted_at ON user_burnout_reports(submitted_at);
    """

    # Function to update the updated_at column
    create_trigger_function_sql = """
    CREATE OR REPLACE FUNCTION update_user_burnout_reports_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """

    create_trigger_sql = """
    DROP TRIGGER IF EXISTS trigger_user_burnout_reports_updated_at ON user_burnout_reports;
    CREATE TRIGGER trigger_user_burnout_reports_updated_at
        BEFORE UPDATE ON user_burnout_reports
        FOR EACH ROW
        EXECUTE FUNCTION update_user_burnout_reports_updated_at();
    """

    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                logger.info("Creating user_burnout_reports table...")
                conn.execute(text(create_table_sql))

                logger.info("Creating indexes...")
                conn.execute(text(create_indexes_sql))

                logger.info("Creating trigger function...")
                conn.execute(text(create_trigger_function_sql))

                logger.info("Creating update trigger...")
                conn.execute(text(create_trigger_sql))

                # Commit transaction
                trans.commit()
                logger.info("✅ Successfully created user_burnout_reports table with indexes and triggers!")

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during table creation: {e}")
                raise

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

    return True

def verify_table_creation(engine):
    """Verify that the table was created successfully."""
    try:
        with engine.connect() as conn:
            # Check if table exists and get column info
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'user_burnout_reports'
                ORDER BY ordinal_position;
            """))

            columns = result.fetchall()
            if not columns:
                logger.error("❌ Table user_burnout_reports was not created!")
                return False

            logger.info("✅ Table verification successful!")
            logger.info("Columns created:")
            for col in columns:
                logger.info(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")

            # Check constraints
            result = conn.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'user_burnout_reports';
            """))

            constraints = result.fetchall()
            logger.info("Constraints:")
            for constraint in constraints:
                logger.info(f"  - {constraint[0]} ({constraint[1]})")

    except SQLAlchemyError as e:
        logger.error(f"❌ Error verifying table: {e}")
        return False

    return True

def main():
    """Run the migration."""
    logger.info("🚀 Starting user_burnout_reports table migration...")

    # Get database URL
    database_url = get_database_url()
    logger.info(f"Database URL: {database_url.split('@')[0] + '@***'}")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            logger.info("✅ Database connection successful!")

        # Create table
        if create_user_burnout_reports_table(engine):
            # Verify creation
            if verify_table_creation(engine):
                logger.info("🎉 Migration completed successfully!")
                logger.info("")
                logger.info("Next steps:")
                logger.info("1. Deploy the new API endpoints")
                logger.info("2. Update the frontend to use user-reported scoring")
                logger.info("3. Test the survey functionality")
                return True

        return False

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)