#!/usr/bin/env python3
"""
SECURE organizations schema migration - SCHEMA ONLY, NO DATA POPULATION.

This migration follows industry security best practices:
- Creates tables and columns only
- NO automatic data population
- NO automatic role assignments
- Full rollback capability
- Comprehensive audit logging

Usage:
    python migrate_organizations_secure.py
"""

import os
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'migration_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
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

def create_backup_tables(engine):
    """Create backup tables for rollback capability."""

    backup_sql = """
    -- Create backup tables for rollback capability
    DO $$
    BEGIN
        -- Backup users table
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users') THEN
            DROP TABLE IF EXISTS users_backup_org_migration;
            CREATE TABLE users_backup_org_migration AS SELECT * FROM users;

            INSERT INTO migration_audit_log (action, status, details, timestamp)
            VALUES ('backup_users', 'success', 'Created users_backup_org_migration', NOW());
        END IF;

        -- Backup analyses table
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'analyses') THEN
            DROP TABLE IF EXISTS analyses_backup_org_migration;
            CREATE TABLE analyses_backup_org_migration AS SELECT * FROM analyses;

            INSERT INTO migration_audit_log (action, status, details, timestamp)
            VALUES ('backup_analyses', 'success', 'Created analyses_backup_org_migration', NOW());
        END IF;

        -- Backup slack_workspace_mappings if exists
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            DROP TABLE IF EXISTS slack_workspace_mappings_backup_org_migration;
            CREATE TABLE slack_workspace_mappings_backup_org_migration AS SELECT * FROM slack_workspace_mappings;

            INSERT INTO migration_audit_log (action, status, details, timestamp)
            VALUES ('backup_slack_workspace_mappings', 'success', 'Created slack_workspace_mappings_backup_org_migration', NOW());
        END IF;
    END $$;
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating backup tables for rollback capability...")
                conn.execute(text(backup_sql))
                trans.commit()
                logger.info("✅ Backup tables created successfully!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error creating backups: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error during backup: {e}")
        return False

def create_audit_log_table(engine):
    """Create migration audit log table."""

    audit_table_sql = """
    -- Create migration audit log table
    CREATE TABLE IF NOT EXISTS migration_audit_log (
        id SERIAL PRIMARY KEY,
        action VARCHAR(100) NOT NULL,
        status VARCHAR(20) NOT NULL,
        details TEXT,
        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_migration_audit_log_timestamp ON migration_audit_log(timestamp);
    CREATE INDEX IF NOT EXISTS idx_migration_audit_log_action ON migration_audit_log(action);

    -- Log audit table creation
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('audit_table_created', 'success', 'Migration audit logging enabled');
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating migration audit log table...")
                conn.execute(text(audit_table_sql))
                trans.commit()
                logger.info("✅ Audit log table created!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error creating audit table: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def create_organizations_table(engine):
    """Create organizations table - SCHEMA ONLY."""

    create_table_sql = """
    -- SECURE: Create organizations table (schema only)
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,

        -- Basic information
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

        -- Status and verification
        status VARCHAR(20) DEFAULT 'pending_verification',  -- SECURE: No auto-active
        domain_verified BOOLEAN DEFAULT FALSE,              -- SECURE: Explicit verification
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        verified_at TIMESTAMP WITH TIME ZONE,

        -- Flexible settings
        settings JSONB DEFAULT '{}',

        -- SECURITY: Strong constraints
        CONSTRAINT organization_name_min_length CHECK (char_length(name) >= 2),
        CONSTRAINT organization_name_max_length CHECK (char_length(name) <= 255),
        CONSTRAINT organization_domain_format CHECK (domain ~ '^[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'),
        CONSTRAINT organization_domain_min_length CHECK (char_length(domain) >= 4),
        CONSTRAINT organization_slug_format CHECK (slug ~ '^[a-z0-9-]+$'),
        CONSTRAINT organization_status_valid CHECK (status IN ('pending_verification', 'active', 'suspended', 'inactive'))
    );

    -- Create indexes for performance and security
    CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain);
    CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
    CREATE INDEX IF NOT EXISTS idx_organizations_status ON organizations(status);
    CREATE INDEX IF NOT EXISTS idx_organizations_domain_verified ON organizations(domain_verified);
    CREATE INDEX IF NOT EXISTS idx_organizations_created_at ON organizations(created_at);

    -- Audit log
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('organizations_table_created', 'success', 'Organizations table created with security constraints');
    """

    # Updated_at trigger
    create_trigger_sql = """
    -- Updated_at trigger for organizations
    CREATE OR REPLACE FUNCTION update_organizations_updated_at()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    DROP TRIGGER IF EXISTS trigger_update_organizations_updated_at ON organizations;
    CREATE TRIGGER trigger_update_organizations_updated_at
        BEFORE UPDATE ON organizations
        FOR EACH ROW
        EXECUTE FUNCTION update_organizations_updated_at();

    -- Audit log
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('organizations_trigger_created', 'success', 'Updated_at trigger created for organizations');
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating organizations table with security constraints...")
                conn.execute(text(create_table_sql))

                logger.info("Creating updated_at trigger...")
                conn.execute(text(create_trigger_sql))

                trans.commit()
                logger.info("✅ Organizations table created successfully with security controls!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error creating organizations table: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def add_organization_columns_secure(engine):
    """Add organization columns to existing tables - SCHEMA ONLY, NO DATA CHANGES."""

    # CRITICAL: This adds columns but does NOT populate them
    alter_users_sql = """
    -- SECURE: Add columns to users table (NO DATA POPULATION)
    ALTER TABLE users
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'user',  -- SECURE: Default to lowest privilege
    ADD COLUMN IF NOT EXISTS joined_org_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

    -- Add security constraints
    ALTER TABLE users
    ADD CONSTRAINT IF NOT EXISTS users_role_valid
    CHECK (role IN ('super_admin', 'org_admin', 'manager', 'user'));

    ALTER TABLE users
    ADD CONSTRAINT IF NOT EXISTS users_status_valid
    CHECK (status IN ('active', 'suspended', 'pending', 'inactive'));

    -- Create indexes
    CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
    CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
    CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
    CREATE INDEX IF NOT EXISTS idx_users_org_role ON users(organization_id, role);

    -- CRITICAL: Verify NO data changes
    DO $$
    DECLARE
        org_assigned_count INTEGER;
        non_user_roles_count INTEGER;
    BEGIN
        SELECT COUNT(*) INTO org_assigned_count FROM users WHERE organization_id IS NOT NULL;
        SELECT COUNT(*) INTO non_user_roles_count FROM users WHERE role != 'user';

        IF org_assigned_count > 0 THEN
            RAISE EXCEPTION 'SECURITY VIOLATION: Users have been assigned to organizations unexpectedly!';
        END IF;

        IF non_user_roles_count > 0 THEN
            RAISE EXCEPTION 'SECURITY VIOLATION: Users have been assigned non-user roles unexpectedly!';
        END IF;
    END $$;

    -- Audit log
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('users_columns_added', 'success', 'Organization columns added to users table, no data populated');
    """

    alter_analyses_sql = """
    -- SECURE: Add organization column to analyses (NO DATA POPULATION)
    ALTER TABLE analyses
    ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL;

    CREATE INDEX IF NOT EXISTS idx_analyses_organization_id ON analyses(organization_id);

    -- CRITICAL: Verify NO data changes
    DO $$
    DECLARE
        org_assigned_count INTEGER;
    BEGIN
        SELECT COUNT(*) INTO org_assigned_count FROM analyses WHERE organization_id IS NOT NULL;

        IF org_assigned_count > 0 THEN
            RAISE EXCEPTION 'SECURITY VIOLATION: Analyses have been assigned to organizations unexpectedly!';
        END IF;
    END $$;

    -- Audit log
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('analyses_columns_added', 'success', 'Organization column added to analyses table, no data populated');
    """

    alter_workspace_mappings_sql = """
    -- SECURE: Add organization column to workspace mappings if exists
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            ALTER TABLE slack_workspace_mappings
            ADD COLUMN IF NOT EXISTS organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL;

            CREATE INDEX IF NOT EXISTS idx_slack_workspace_mappings_organization_id
            ON slack_workspace_mappings(organization_id);

            -- CRITICAL: Verify NO data changes
            DECLARE
                org_assigned_count INTEGER;
            BEGIN
                SELECT COUNT(*) INTO org_assigned_count FROM slack_workspace_mappings WHERE organization_id IS NOT NULL;

                IF org_assigned_count > 0 THEN
                    RAISE EXCEPTION 'SECURITY VIOLATION: Workspace mappings have been assigned to organizations unexpectedly!';
                END IF;
            END;

            INSERT INTO migration_audit_log (action, status, details)
            VALUES ('workspace_mappings_columns_added', 'success', 'Organization column added to slack_workspace_mappings, no data populated');
        END IF;
    END $$;
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Adding organization columns to users table (NO DATA POPULATION)...")
                conn.execute(text(alter_users_sql))

                logger.info("Adding organization columns to analyses table (NO DATA POPULATION)...")
                conn.execute(text(alter_analyses_sql))

                logger.info("Adding organization columns to workspace mappings (NO DATA POPULATION)...")
                conn.execute(text(alter_workspace_mappings_sql))

                trans.commit()
                logger.info("✅ Organization columns added successfully with security verification!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error adding columns: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def create_organization_invitations_table(engine):
    """Create secure invitation system table."""

    invitations_table_sql = """
    -- Create secure organization invitations table
    CREATE TABLE IF NOT EXISTS organization_invitations (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
        email VARCHAR(255) NOT NULL,
        role VARCHAR(20) NOT NULL DEFAULT 'user',
        token_hash VARCHAR(255) NOT NULL UNIQUE,  -- Hashed token for security
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        invited_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        used_at TIMESTAMP WITH TIME ZONE,
        status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'accepted', 'expired', 'revoked'

        -- Security constraints
        CONSTRAINT invitation_role_valid CHECK (role IN ('org_admin', 'manager', 'user')),
        CONSTRAINT invitation_status_valid CHECK (status IN ('pending', 'accepted', 'expired', 'revoked')),
        CONSTRAINT invitation_expires_future CHECK (expires_at > created_at),
        CONSTRAINT invitation_email_format CHECK (email ~ '^[^@]+@[^@]+\\.[^@]+$')
    );

    -- Indexes for security and performance
    CREATE INDEX IF NOT EXISTS idx_organization_invitations_token_hash ON organization_invitations(token_hash);
    CREATE INDEX IF NOT EXISTS idx_organization_invitations_email ON organization_invitations(email);
    CREATE INDEX IF NOT EXISTS idx_organization_invitations_org_id ON organization_invitations(organization_id);
    CREATE INDEX IF NOT EXISTS idx_organization_invitations_expires_at ON organization_invitations(expires_at);
    CREATE INDEX IF NOT EXISTS idx_organization_invitations_status ON organization_invitations(status);

    -- Audit log
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('invitations_table_created', 'success', 'Organization invitations table created with security controls');
    """

    try:
        with engine.connect() as conn:
            trans = conn.begin()
            try:
                logger.info("Creating organization invitations table...")
                conn.execute(text(invitations_table_sql))
                trans.commit()
                logger.info("✅ Organization invitations table created!")
                return True
            except Exception as e:
                trans.rollback()
                logger.error(f"❌ Error creating invitations table: {e}")
                raise
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}")
        return False

def verify_secure_migration(engine):
    """Verify that the migration is secure and no unintended data changes occurred."""

    verification_sql = """
    -- CRITICAL SECURITY VERIFICATION
    SELECT
        -- Organizations should be empty
        (SELECT COUNT(*) FROM organizations) as organizations_count,

        -- NO users should be assigned to organizations
        (SELECT COUNT(*) FROM users WHERE organization_id IS NOT NULL) as users_assigned_to_orgs,

        -- ALL users should have 'user' role
        (SELECT COUNT(*) FROM users WHERE role != 'user') as users_with_elevated_roles,

        -- NO analyses should be assigned to organizations
        (SELECT COUNT(*) FROM analyses WHERE organization_id IS NOT NULL) as analyses_assigned_to_orgs,

        -- Check workspace mappings if they exist
        CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings')
        THEN (SELECT COUNT(*) FROM slack_workspace_mappings WHERE organization_id IS NOT NULL)
        ELSE 0 END as workspace_mappings_assigned_to_orgs,

        -- Verify backup tables exist
        CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users_backup_org_migration')
        THEN 1 ELSE 0 END as users_backup_exists,

        CASE WHEN EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'analyses_backup_org_migration')
        THEN 1 ELSE 0 END as analyses_backup_exists
    """

    try:
        with engine.connect() as conn:
            result = conn.execute(text(verification_sql))
            verification_data = result.fetchone()

            logger.info("🔍 SECURITY VERIFICATION RESULTS:")
            logger.info(f"  Organizations created: {verification_data[0]} (should be 0)")
            logger.info(f"  Users assigned to orgs: {verification_data[1]} (should be 0)")
            logger.info(f"  Users with elevated roles: {verification_data[2]} (should be 0)")
            logger.info(f"  Analyses assigned to orgs: {verification_data[3]} (should be 0)")
            logger.info(f"  Workspace mappings assigned: {verification_data[4]} (should be 0)")
            logger.info(f"  Users backup exists: {verification_data[5]} (should be 1)")
            logger.info(f"  Analyses backup exists: {verification_data[6]} (should be 1)")

            # CRITICAL: Verify security invariants
            if verification_data[1] > 0:  # users_assigned_to_orgs
                raise Exception("🚨 SECURITY VIOLATION: Users have been assigned to organizations!")

            if verification_data[2] > 0:  # users_with_elevated_roles
                raise Exception("🚨 SECURITY VIOLATION: Users have elevated roles!")

            if verification_data[3] > 0:  # analyses_assigned_to_orgs
                raise Exception("🚨 SECURITY VIOLATION: Analyses have been assigned to organizations!")

            if verification_data[4] > 0:  # workspace_mappings_assigned_to_orgs
                raise Exception("🚨 SECURITY VIOLATION: Workspace mappings have been assigned to organizations!")

            if verification_data[5] == 0:  # users_backup_exists
                raise Exception("🚨 ROLLBACK RISK: Users backup table does not exist!")

            # Log successful verification
            conn.execute(text("""
                INSERT INTO migration_audit_log (action, status, details)
                VALUES ('security_verification', 'success', 'All security invariants verified - no unauthorized data changes')
            """))

            logger.info("✅ SECURITY VERIFICATION PASSED - Migration is secure!")
            return True

    except Exception as e:
        logger.error(f"❌ SECURITY VERIFICATION FAILED: {e}")
        conn.execute(text(f"""
            INSERT INTO migration_audit_log (action, status, details)
            VALUES ('security_verification', 'failed', 'Security verification failed: {str(e)}')
        """))
        return False

def create_rollback_script(engine):
    """Create rollback script for complete migration reversal."""

    rollback_script = '''#!/usr/bin/env python3
"""
ROLLBACK SCRIPT - Completely reverses organization migration.
Run this script to restore the database to pre-migration state.
"""

import sys
from sqlalchemy import create_engine, text

def rollback_migration():
    """Complete rollback of organizations migration."""
    engine = create_engine(sys.argv[1] if len(sys.argv) > 1 else input("Database URL: "))

    rollback_sql = """
    -- ROLLBACK: Complete migration reversal
    BEGIN;

    -- Drop organization-related tables
    DROP TABLE IF EXISTS organization_invitations;
    DROP TABLE IF EXISTS organizations CASCADE;

    -- Remove organization columns from users
    ALTER TABLE users DROP COLUMN IF EXISTS organization_id;
    ALTER TABLE users DROP COLUMN IF EXISTS role;
    ALTER TABLE users DROP COLUMN IF EXISTS joined_org_at;
    ALTER TABLE users DROP COLUMN IF EXISTS last_active_at;
    ALTER TABLE users DROP COLUMN IF EXISTS status;

    -- Remove organization columns from analyses
    ALTER TABLE analyses DROP COLUMN IF EXISTS organization_id;

    -- Remove organization columns from slack_workspace_mappings if exists
    DO $$
    BEGIN
        IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'slack_workspace_mappings') THEN
            ALTER TABLE slack_workspace_mappings DROP COLUMN IF EXISTS organization_id;
        END IF;
    END $$;

    -- Clean up backup tables (optional)
    -- DROP TABLE IF EXISTS users_backup_org_migration;
    -- DROP TABLE IF EXISTS analyses_backup_org_migration;
    -- DROP TABLE IF EXISTS slack_workspace_mappings_backup_org_migration;

    -- Log rollback
    INSERT INTO migration_audit_log (action, status, details)
    VALUES ('migration_rollback', 'success', 'Organizations migration completely rolled back');

    COMMIT;
    """

    with engine.connect() as conn:
        conn.execute(text(rollback_sql))
        print("✅ Migration rolled back successfully!")

if __name__ == "__main__":
    rollback_migration()
'''

    # Write rollback script to file
    with open('rollback_organizations_migration.py', 'w') as f:
        f.write(rollback_script)

    os.chmod('rollback_organizations_migration.py', 0o755)

    logger.info("✅ Rollback script created: rollback_organizations_migration.py")
    return True

def main():
    """Run the SECURE organizations schema migration."""
    logger.info("🔒 Starting SECURE organizations schema migration...")
    logger.info("🚨 SECURITY MODE: Schema only, NO data population, NO automatic role assignments")

    # Get database URL
    database_url = get_database_url()
    logger.info(f"Database URL: {database_url.split('@')[0] + '@***'}")

    try:
        # Create engine
        engine = create_engine(database_url)

        # Test connection
        with engine.connect() as conn:
            logger.info("✅ Database connection successful!")

        # Step 1: Create audit log table
        if not create_audit_log_table(engine):
            return False

        # Step 2: Create backup tables for rollback
        if not create_backup_tables(engine):
            return False

        # Step 3: Create organizations table (empty)
        if not create_organizations_table(engine):
            return False

        # Step 4: Add organization columns (no data population)
        if not add_organization_columns_secure(engine):
            return False

        # Step 5: Create invitation system
        if not create_organization_invitations_table(engine):
            return False

        # Step 6: Security verification
        if not verify_secure_migration(engine):
            return False

        # Step 7: Create rollback script
        if not create_rollback_script(engine):
            return False

        logger.info("🎉 SECURE organizations schema migration completed successfully!")
        logger.info("")
        logger.info("🔐 SECURITY SUMMARY:")
        logger.info("✅ Schema created with security constraints")
        logger.info("✅ NO automatic data population")
        logger.info("✅ NO automatic role assignments")
        logger.info("✅ Backup tables created for rollback")
        logger.info("✅ Security verification passed")
        logger.info("✅ Rollback script created")
        logger.info("")
        logger.info("📋 NEXT STEPS (MANUAL):")
        logger.info("1. Deploy updated application code")
        logger.info("2. Super admin creates organizations via secure API")
        logger.info("3. Super admin invites org admins via invitation system")
        logger.info("4. Org admins invite users to their organizations")
        logger.info("5. Gradually migrate existing data with explicit approval")
        logger.info("")
        logger.info("🆘 ROLLBACK: Run ./rollback_organizations_migration.py to reverse")

        return True

    except Exception as e:
        logger.error(f"❌ SECURE migration failed: {e}")
        logger.error("🆘 Database state may be inconsistent - check logs and consider rollback")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)