#!/usr/bin/env python3
"""
Simple organizations MVP migration - creates orgs from email domains and assigns first user as admin.

Usage:
    python migrate_organizations_mvp.py
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
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')

    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')
    database = os.getenv('POSTGRES_DATABASE', 'burnout_detector')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"

def create_organizations_table(engine):
    """Create organizations table."""

    sql = """
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        domain VARCHAR(255) UNIQUE NOT NULL,
        slug VARCHAR(100) UNIQUE NOT NULL,
        status VARCHAR(20) DEFAULT 'active',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);

    -- Create invitations table for Gmail/shared domain users
    CREATE TABLE IF NOT EXISTS organization_invitations (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER REFERENCES organizations(id),
        email VARCHAR(255) NOT NULL,
        role VARCHAR(20) DEFAULT 'user',
        invited_by INTEGER REFERENCES users(id),
        token VARCHAR(255) UNIQUE,
        expires_at TIMESTAMP WITH TIME ZONE,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_invitations_email ON organization_invitations(email);
    CREATE INDEX IF NOT EXISTS idx_invitations_token ON organization_invitations(token);

    -- Create notifications table for integrations page
    CREATE TABLE IF NOT EXISTS user_notifications (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        email VARCHAR(255),
        organization_id INTEGER REFERENCES organizations(id),
        type VARCHAR(50) NOT NULL,
        title VARCHAR(255) NOT NULL,
        message TEXT,
        action_url VARCHAR(500),
        action_text VARCHAR(100),
        organization_invitation_id INTEGER REFERENCES organization_invitations(id),
        analysis_id INTEGER REFERENCES analyses(id),
        status VARCHAR(20) DEFAULT 'unread',
        priority VARCHAR(20) DEFAULT 'normal',
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        read_at TIMESTAMP WITH TIME ZONE,
        expires_at TIMESTAMP WITH TIME ZONE
    );

    CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON user_notifications(user_id);
    CREATE INDEX IF NOT EXISTS idx_notifications_email ON user_notifications(email);
    CREATE INDEX IF NOT EXISTS idx_notifications_status ON user_notifications(status);
    CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON user_notifications(created_at);
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating organizations table...")
                conn.execute(text(sql))
                trans.commit()
                logger.info("✅ Organizations table created!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def add_organization_columns(engine):
    """Add organization columns to existing tables."""

    sql = """
    -- Add organization columns
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id),
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS joined_org_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

    ALTER TABLE analyses
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);

    -- Update workspace mappings if exists
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            ALTER TABLE slack_workspace_mappings
            ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id);
        END IF;
    END $$;

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
    CREATE INDEX IF NOT EXISTS idx_analyses_organization_id ON analyses(organization_id);
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Adding organization columns...")
                conn.execute(text(sql))
                trans.commit()
                logger.info("✅ Organization columns added!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def populate_organizations(engine):
    """Create organizations from email domains and assign users."""

    sql = """
    -- Create organizations from unique email domains (excluding shared domains)
    WITH domain_stats AS (
        SELECT
            SUBSTRING(email FROM '@(.*)$') as domain,
            COUNT(*) as user_count,
            MIN(id) as first_user_id
        FROM users
        WHERE email IS NOT NULL
          AND email LIKE '%@%'
          AND SUBSTRING(email FROM '@(.*)$') NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com')
        GROUP BY SUBSTRING(email FROM '@(.*)$')
    )
    INSERT INTO organizations (name, domain, slug)
    SELECT
        REPLACE(INITCAP(REPLACE(domain, '.com', '')), '.', ' ') || ' Organization' as name,
        domain,
        REPLACE(LOWER(domain), '.', '-') as slug
    FROM domain_stats
    WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE organizations.domain = domain_stats.domain);

    -- Assign users to organizations (only for company domains, not shared domains)
    UPDATE users
    SET organization_id = o.id,
        role = CASE
            WHEN users.id = (
                SELECT MIN(u2.id) FROM users u2
                WHERE SUBSTRING(u2.email FROM '@(.*)$') = o.domain
            ) THEN 'org_admin'
            ELSE 'user'
        END
    FROM organizations o
    WHERE SUBSTRING(users.email FROM '@(.*)$') = o.domain
      AND SUBSTRING(users.email FROM '@(.*)$') NOT IN ('gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com');

    -- Assign analyses to organizations
    UPDATE analyses
    SET organization_id = u.organization_id
    FROM users u
    WHERE analyses.user_id = u.id;

    -- Assign workspace mappings to organizations if exists
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            UPDATE slack_workspace_mappings
            SET organization_id = u.organization_id
            FROM users u
            WHERE slack_workspace_mappings.owner_user_id = u.id;
        END IF;
    END $$;
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating organizations and assigning users...")
                conn.execute(text(sql))
                trans.commit()
                logger.info("✅ Organizations populated!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def verify_migration(engine):
    """Verify migration results."""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    o.name,
                    o.domain,
                    COUNT(u.id) as users,
                    COUNT(CASE WHEN u.role = 'org_admin' THEN 1 END) as admins
                FROM organizations o
                LEFT JOIN users u ON o.id = u.organization_id
                GROUP BY o.id, o.name, o.domain
                ORDER BY users DESC
            """))

            orgs = result.fetchall()
            logger.info(f"✅ Created {len(orgs)} organizations:")
            for org in orgs:
                logger.info(f"  - {org[0]} ({org[1]}): {org[2]} users, {org[3]} admins")

            return True
    except SQLAlchemyError as e:
        logger.error(f"❌ Verification error: {e}")
        return False

def main():
    """Run the MVP organizations migration."""
    logger.info("🚀 Starting MVP organizations migration...")

    database_url = get_database_url()
    logger.info(f"Database URL: {database_url.split('@')[0] + '@***'}")

    try:
        engine = create_engine(database_url)

        with engine.connect() as conn:
            logger.info("✅ Database connection successful!")

        if not create_organizations_table(engine):
            return False

        if not add_organization_columns(engine):
            return False

        if not populate_organizations(engine):
            return False

        if not verify_migration(engine):
            return False

        logger.info("🎉 MVP organizations migration completed!")
        return True

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)