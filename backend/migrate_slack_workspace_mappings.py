#!/usr/bin/env python3
"""
Migration script to create slack_workspace_mappings table for multi-org Slack support.

This enables proper organization isolation for Slack slash commands across multiple tenants.

Usage:
    python migrate_slack_workspace_mappings.py
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

def create_slack_workspace_mappings_table(engine):
    """Create the slack_workspace_mappings table for multi-org support."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS slack_workspace_mappings (
        id SERIAL PRIMARY KEY,

        -- Slack workspace identification
        workspace_id VARCHAR(20) NOT NULL UNIQUE,  -- T01234567 (Slack team ID)
        workspace_name VARCHAR(255),               -- "Acme Corp"
        workspace_domain VARCHAR(255),             -- "acme-corp.slack.com"

        -- Organization mapping
        owner_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        organization_domain VARCHAR(255),          -- "company.com"

        -- Registration tracking
        registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        registered_via VARCHAR(20) DEFAULT 'oauth',  -- 'oauth', 'manual', 'admin'

        -- Status and management
        status VARCHAR(20) DEFAULT 'active',       -- 'active', 'suspended', 'pending'

        -- Constraints
        CONSTRAINT unique_workspace_id UNIQUE(workspace_id)
    );
    """

    create_indexes_sql = """
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_owner_user_id ON slack_workspace_mappings(owner_user_id);
    CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_workspace_id ON slack_workspace_mappings(workspace_id);
    CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_status ON slack_workspace_mappings(status);
    CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_domain ON slack_workspace_mappings(organization_domain);
    """

    # Function to update the updated_at column (if needed in future)
    create_trigger_function_sql = """
    -- Future-proofing: trigger function for updated_at column
    CREATE OR REPLACE FUNCTION update_slack_workspace_mappings_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    """

    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()

            try:
                logger.info("Creating slack_workspace_mappings table...")
                conn.execute(text(create_table_sql))

                logger.info("Creating indexes...")
                conn.execute(text(create_indexes_sql))

                logger.info("Creating trigger function for future use...")
                conn.execute(text(create_trigger_function_sql))

                # Commit transaction
                trans.commit()
                logger.info("✅ Successfully created slack_workspace_mappings table!")

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during table creation: {e}")
                raise

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

    return True

def migrate_existing_slack_integrations(engine):
    """Migrate existing Slack integrations to workspace mappings."""

    migrate_sql = """
    -- Create workspace mappings from existing slack_integrations
    INSERT INTO slack_workspace_mappings (
        workspace_id,
        workspace_name,
        owner_user_id,
        registered_via,
        status
    )
    SELECT DISTINCT
        si.workspace_id,
        'Legacy Workspace' as workspace_name,
        si.user_id as owner_user_id,
        'legacy' as registered_via,
        'active' as status
    FROM slack_integrations si
    WHERE si.workspace_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM slack_workspace_mappings swm
          WHERE swm.workspace_id = si.workspace_id
      );
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Migrating existing Slack integrations...")
                result = conn.execute(text(migrate_sql))
                migrated_count = result.rowcount

                trans.commit()
                logger.info(f"✅ Migrated {migrated_count} existing Slack workspace(s)")
                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during migration: {e}")
                raise

    except SQLAlchemyError as e:
        logger.error(f"❌ Migration error: {e}")
        return False

def verify_table_creation(engine):
    """Verify that the table was created successfully."""
    try:
        with engine.connect() as conn:
            # Check if table exists and get column info
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'slack_workspace_mappings'
                ORDER BY ordinal_position;
            """))

            columns = result.fetchall()
            if not columns:
                logger.error("❌ Table slack_workspace_mappings was not created!")
                return False

            logger.info("✅ Table verification successful!")
            logger.info("Columns created:")
            for col in columns:
                logger.info(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")

            # Check constraints
            result = conn.execute(text("""
                SELECT constraint_name, constraint_type
                FROM information_schema.table_constraints
                WHERE table_name = 'slack_workspace_mappings';
            """))

            constraints = result.fetchall()
            logger.info("Constraints:")
            for constraint in constraints:
                logger.info(f"  - {constraint[0]} ({constraint[1]})")

            # Show sample data if any exists
            result = conn.execute(text("SELECT COUNT(*) FROM slack_workspace_mappings"))
            count = result.scalar()
            logger.info(f"Workspace mappings in table: {count}")

    except SQLAlchemyError as e:
        logger.error(f"❌ Error verifying table: {e}")
        return False

    return True

def main():
    """Run the migration."""
    logger.info("🚀 Starting slack_workspace_mappings table migration...")

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
        if create_slack_workspace_mappings_table(engine):
            # Migrate existing data
            migrate_existing_slack_integrations(engine)

            # Verify creation
            if verify_table_creation(engine):
                logger.info("🎉 Migration completed successfully!")
                logger.info("")
                logger.info("Next steps:")
                logger.info("1. Update Slack OAuth flow to create workspace mappings")
                logger.info("2. Update slash command to use organization-scoped queries")
                logger.info("3. Add 'Add to Slack' button to manager dashboard")
                logger.info("4. Configure centralized Slack app with proper OAuth redirect")
                return True

        return False

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)