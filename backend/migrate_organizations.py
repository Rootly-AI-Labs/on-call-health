#!/usr/bin/env python3
"""
Migration script to create organizations table and update existing tables for multi-org support.

This enables proper organization-based user management and data isolation.

Usage:
    python migrate_organizations.py
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

def create_organizations_table(engine):
    """Create the organizations table."""

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        domain VARCHAR(255) UNIQUE NOT NULL,
        slug VARCHAR(100) UNIQUE NOT NULL,

        -- Contact information
        primary_contact_email VARCHAR(255),
        billing_email VARCHAR(255),
        website VARCHAR(255),

        -- Subscription and limits
        plan_type VARCHAR(50) DEFAULT 'free',
        max_users INTEGER DEFAULT 50,
        max_analyses_per_month INTEGER DEFAULT 5,

        -- Status and timestamps
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

        -- Flexible settings as JSON
        settings JSONB DEFAULT '{}',

        -- Constraints
        CONSTRAINT organization_name_min_length CHECK (char_length(name) >= 2),
        CONSTRAINT organization_domain_format CHECK (domain ~ '^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$')
    );
    """

    create_indexes_sql = """
    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);
    CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
    CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);
    CREATE INDEX IF NOT EXISTS idx_organizations_plan_type ON organizations(plan_type);
    """

    # Function to update the updated_at column
    create_trigger_function_sql = """
    -- Trigger function for updated_at column
    CREATE OR REPLACE FUNCTION update_organizations_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    -- Create trigger
    DROP TRIGGER IF EXISTS trigger_update_organizations_updated_at ON organizations;
    CREATE TRIGGER trigger_update_organizations_updated_at
        BEFORE UPDATE ON organizations
        FOR EACH ROW
        EXECUTE FUNCTION update_organizations_updated_at();
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating organizations table...")
                conn.execute(text(create_table_sql))

                logger.info("Creating indexes...")
                conn.execute(text(create_indexes_sql))

                logger.info("Creating trigger function...")
                conn.execute(text(create_trigger_function_sql))

                trans.commit()
                logger.info("✅ Successfully created organizations table!")
                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during organizations table creation: {e}")
                raise

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def add_organization_columns(engine):
    """Add organization_id and role columns to existing tables."""

    alter_users_sql = """
    -- Add organization and role columns to users table
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id),
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS joined_org_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
    """

    alter_analyses_sql = """
    -- Add organization_id to analyses table
    ALTER TABLE analyses
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);

    -- Create index
    CREATE INDEX IF NOT EXISTS idx_analyses_organization_id ON analyses(organization_id);
    """

    alter_workspace_mappings_sql = """
    -- Add organization_id to slack_workspace_mappings table (if exists)
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            ALTER TABLE slack_workspace_mappings
            ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);

            CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_organization_id
            ON slack_workspace_mappings(organization_id);
        END IF;
    END $$;
    """

    alter_burnout_reports_sql = """
    -- Add organization_id to user_burnout_reports table (if exists)
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'user_burnout_reports') THEN
            ALTER TABLE user_burnout_reports
            ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);

            CREATE INDEX IF NOT EXISTS idx_user_burnout_reports_organization_id
            ON user_burnout_reports(organization_id);
        END IF;
    END $$;
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Adding organization columns to users table...")
                conn.execute(text(alter_users_sql))

                logger.info("Adding organization columns to analyses table...")
                conn.execute(text(alter_analyses_sql))

                logger.info("Adding organization columns to slack_workspace_mappings table...")
                conn.execute(text(alter_workspace_mappings_sql))

                logger.info("Adding organization columns to user_burnout_reports table...")
                conn.execute(text(alter_burnout_reports_sql))

                trans.commit()
                logger.info("✅ Successfully added organization columns!")
                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during column addition: {e}")
                raise

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def populate_organizations_from_users(engine):
    """Auto-create organizations from existing user email domains."""

    create_orgs_sql = """
    -- Create organizations from unique email domains
    WITH domain_stats AS (
        SELECT
            SUBSTRING(email FROM '@(.*)$') as domain,
            COUNT(*) as user_count,
            MIN(created_at) as earliest_user,
            MIN(id) as first_user_id
        FROM users
        WHERE email IS NOT NULL
          AND email LIKE '%@%'
          AND SUBSTRING(email FROM '@(.*)$') ~ '^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
        GROUP BY SUBSTRING(email FROM '@(.*)$')
        HAVING COUNT(*) > 0
    )
    INSERT INTO organizations (name, domain, slug, primary_contact_email, status, created_at)
    SELECT
        INITCAP(REPLACE(REPLACE(domain, '.com', ''), '.', ' ')) || ' Organization' as name,
        domain,
        REPLACE(LOWER(domain), '.', '-') as slug,
        'admin@' || domain as primary_contact_email,
        'active' as status,
        earliest_user as created_at
    FROM domain_stats
    WHERE NOT EXISTS (
        SELECT 1 FROM organizations WHERE organizations.domain = domain_stats.domain
    )
    ORDER BY user_count DESC;
    """

    assign_users_to_orgs_sql = """
    -- Assign users to organizations and set roles
    UPDATE users
    SET
        organization_id = o.id,
        role = CASE
            WHEN users.id = (
                SELECT MIN(u2.id)
                FROM users u2
                WHERE SUBSTRING(u2.email FROM '@(.*)$') = o.domain
                ORDER BY u2.created_at ASC
                LIMIT 1
            ) THEN 'org_admin'  -- First user becomes admin
            ELSE 'user'
        END,
        joined_org_at = COALESCE(users.created_at, CURRENT_TIMESTAMP)
    FROM organizations o
    WHERE SUBSTRING(users.email FROM '@(.*)$') = o.domain
      AND users.organization_id IS NULL;
    """

    assign_analyses_to_orgs_sql = """
    -- Assign analyses to organizations based on user
    UPDATE analyses
    SET organization_id = u.organization_id
    FROM users u
    WHERE analyses.user_id = u.id
      AND analyses.organization_id IS NULL
      AND u.organization_id IS NOT NULL;
    """

    assign_workspace_mappings_to_orgs_sql = """
    -- Assign workspace mappings to organizations (if table exists)
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            UPDATE slack_workspace_mappings
            SET organization_id = u.organization_id,
                organization_domain = o.domain
            FROM users u, organizations o
            WHERE slack_workspace_mappings.owner_user_id = u.id
              AND u.organization_id = o.id
              AND slack_workspace_mappings.organization_id IS NULL;
        END IF;
    END $$;
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating organizations from user email domains...")
                result = conn.execute(text(create_orgs_sql))
                logger.info(f"Created organizations for unique domains")

                logger.info("Assigning users to organizations...")
                result = conn.execute(text(assign_users_to_orgs_sql))
                logger.info(f"Assigned users to organizations")

                logger.info("Assigning analyses to organizations...")
                result = conn.execute(text(assign_analyses_to_orgs_sql))
                logger.info(f"Assigned analyses to organizations")

                logger.info("Assigning workspace mappings to organizations...")
                result = conn.execute(text(assign_workspace_mappings_to_orgs_sql))
                logger.info(f"Assigned workspace mappings to organizations")

                trans.commit()
                logger.info("✅ Successfully populated organizations!")
                return True

            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error during organization population: {e}")
                raise

    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def verify_migration(engine):
    """Verify that the migration completed successfully."""
    try:
        with engine.connect() as conn:
            # Check organizations
            result = conn.execute(text("SELECT COUNT(*) FROM organizations"))
            org_count = result.scalar()
            logger.info(f"Organizations created: {org_count}")

            # Check users with organizations
            result = conn.execute(text("""
                SELECT COUNT(*) FROM users WHERE organization_id IS NOT NULL
            """))
            users_with_orgs = result.scalar()
            logger.info(f"Users assigned to organizations: {users_with_orgs}")

            # Check org admins
            result = conn.execute(text("""
                SELECT COUNT(*) FROM users WHERE role = 'org_admin'
            """))
            org_admin_count = result.scalar()
            logger.info(f"Organization admins: {org_admin_count}")

            # Show organizations summary
            result = conn.execute(text("""
                SELECT
                    o.name,
                    o.domain,
                    COUNT(u.id) as user_count,
                    COUNT(CASE WHEN u.role = 'org_admin' THEN 1 END) as admin_count
                FROM organizations o
                LEFT JOIN users u ON o.id = u.organization_id
                GROUP BY o.id, o.name, o.domain
                ORDER BY user_count DESC
            """))

            orgs = result.fetchall()
            logger.info("Organizations summary:")
            for org in orgs:
                logger.info(f"  - {org[0]} ({org[1]}): {org[2]} users, {org[3]} admins")

            return True

    except SQLAlchemyError as e:
        logger.error(f"❌ Error verifying migration: {e}")
        return False

def main():
    """Run the organizations migration."""
    logger.info("🚀 Starting organizations migration...")

    # Get database URL
    database_url = get_database_url()
    logger.info(f"Database URL: {database_url.split('@')[0] + '@***'}")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            logger.info("✅ Database connection successful!")

        # Step 1: Create organizations table
        if not create_organizations_table(engine):
            return False

        # Step 2: Add organization columns to existing tables
        if not add_organization_columns(engine):
            return False

        # Step 3: Populate organizations from existing data
        if not populate_organizations_from_users(engine):
            return False

        # Step 4: Verify migration
        if not verify_migration(engine):
            return False

        logger.info("🎉 Organizations migration completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Deploy updated application code with Organization model")
        logger.info("2. Update authentication to use organization-scoped permissions")
        logger.info("3. Add organization management UI to dashboard")
        logger.info("4. Update Slack integration to use organization correlation")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)