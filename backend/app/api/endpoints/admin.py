"""
Admin endpoints for database maintenance and fixes.
"""
import json
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ...auth.dependencies import get_current_active_user
from ...core.rate_limiting import admin_rate_limit, limiter
from ...models import Analysis, get_db
from ...models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# Security Configuration
# ----------------------
# ADMIN_API_KEY: Required for sensitive admin operations.
# Must be at least 32 characters for security. Store in secrets manager (AWS Secrets Manager,
# HashiCorp Vault, etc.) rather than plain environment variables in production.
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
MIN_API_KEY_LENGTH = 32

# ADMIN_IP_WHITELIST: Optional comma-separated list of allowed IP addresses/CIDR ranges
# Example: "10.0.0.1,192.168.1.0/24,203.0.113.50"
# If not set, IP whitelist is disabled (all IPs allowed if API key is valid)
ADMIN_IP_WHITELIST = os.getenv("ADMIN_IP_WHITELIST", "").strip()

def _parse_ip_whitelist() -> set:
    """Parse the IP whitelist from environment variable."""
    if not ADMIN_IP_WHITELIST:
        return set()
    return {ip.strip() for ip in ADMIN_IP_WHITELIST.split(",") if ip.strip()}

def _is_ip_whitelisted(client_ip: str, whitelist: set) -> bool:
    """Check if client IP is in the whitelist. Supports exact match only for simplicity."""
    if not whitelist:
        return True  # No whitelist configured, allow all
    return client_ip in whitelist

def _validate_admin_api_key() -> bool:
    """Validate that ADMIN_API_KEY meets security requirements."""
    if not ADMIN_API_KEY:
        return False
    if len(ADMIN_API_KEY) < MIN_API_KEY_LENGTH:
        logger.error(
            f"SECURITY: ADMIN_API_KEY is too short ({len(ADMIN_API_KEY)} chars). "
            f"Minimum required: {MIN_API_KEY_LENGTH} chars. Admin endpoints will be disabled."
        )
        return False
    return True

# Validate API key at module load time
_admin_api_key_valid = _validate_admin_api_key()
_ip_whitelist = _parse_ip_whitelist()

if _ip_whitelist:
    logger.info(f"SECURITY: Admin IP whitelist enabled with {len(_ip_whitelist)} entries")

@router.post("/fix-null-organizations")
async def fix_null_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Fix historical analyses that have null organization names.
    This is a one-time maintenance endpoint.
    """

    # Security check: Only admins can run this
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    # SECURITY: Filter by organization to prevent cross-org data modification
    analyses = db.query(Analysis).filter(
        Analysis.results.isnot(None),
        Analysis.organization_id == current_user.organization_id
    ).all()
    
    updated_count = 0
    analysis_details = []
    
    for analysis in analyses:
        if analysis.results and isinstance(analysis.results, dict):
            metadata = analysis.results.get('metadata', {})
            
            # Check if organization_name is null or missing
            current_org_name = metadata.get('organization_name')
            if current_org_name is None or current_org_name == 'null':
                # Use generic fallback for null organization names
                new_org_name = "Organization"

                # Update the organization name
                metadata['organization_name'] = new_org_name
                analysis.results['metadata'] = metadata
                
                # Mark as modified
                db.add(analysis)
                updated_count += 1
                
                analysis_details.append({
                    "id": analysis.id,
                    "created_at": analysis.created_at.isoformat(),
                    "old_name": current_org_name,
                    "new_name": new_org_name
                })
    
    if updated_count > 0:
        db.commit()
    
    # Get summary of organization names after update
    org_summary = {}
    total_analyses = 0
    
    for analysis in analyses:
        if analysis.results and isinstance(analysis.results, dict):
            metadata = analysis.results.get('metadata', {})
            org_name = metadata.get('organization_name', 'Unknown')
            org_summary[org_name] = org_summary.get(org_name, 0) + 1
            total_analyses += 1
    
    return {
        "status": "success",
        "updated_count": updated_count,
        "total_analyses": total_analyses,
        "organization_summary": org_summary,
        "updated_analyses": analysis_details[:10],  # Show first 10 for brevity
        "message": f"Updated {updated_count} analyses with proper organization names"
    }

@router.post("/migrate-slack-workspace-mappings")
async def migrate_slack_workspace_mappings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Create slack_workspace_mappings table and migrate existing Slack integrations.
    This is a one-time migration endpoint for multi-org Slack support.
    """

    # Security check: Only admins can run migrations
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

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

    migrate_existing_sql = """
    -- Migrate existing slack_integrations to workspace mappings
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
        # Start transaction
        results = {}

        # Create table
        db.execute(text(create_table_sql))
        results["table_created"] = True

        # Create indexes
        db.execute(text(create_indexes_sql))
        results["indexes_created"] = True

        # Create trigger function
        db.execute(text(create_trigger_function_sql))
        results["trigger_function_created"] = True

        # Migrate existing integrations
        migration_result = db.execute(text(migrate_existing_sql))
        migrated_count = migration_result.rowcount
        results["migrated_count"] = migrated_count

        # Commit all changes
        db.commit()

        # Verify table creation
        verify_result = db.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'slack_workspace_mappings'
            ORDER BY ordinal_position;
        """))
        columns = verify_result.fetchall()
        results["columns"] = [{"name": col[0], "type": col[1], "nullable": col[2]} for col in columns]

        # Get count of workspace mappings
        count_result = db.execute(text("SELECT COUNT(*) FROM slack_workspace_mappings"))
        total_count = count_result.scalar()
        results["total_workspace_mappings"] = total_count

        return {
            "status": "success",
            "message": f"Successfully created slack_workspace_mappings table and migrated {migrated_count} existing workspace(s)",
            "results": results
        }

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during migration: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")

@router.post("/migrate-organizations")
async def migrate_organizations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Run the complete organizations migration - creates organizations, invitations, and notifications tables.
    This is a one-time migration for multi-org support.
    """

    # Security check: Only admins can run migrations
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        # Import and run the migration
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

        from migrate_organizations_mvp import (
            create_organizations_table,
            add_organization_columns,
            populate_organizations,
            verify_migration,
            get_database_url
        )
        from sqlalchemy import create_engine

        # Create engine using the same database URL
        database_url = get_database_url()
        engine = create_engine(database_url)

        results = {}

        # Step 1: Create organizations table
        if create_organizations_table(engine):
            results["organizations_table"] = "created"
        else:
            results["organizations_table"] = "failed"
            return {"status": "error", "results": results}

        # Step 2: Add organization columns
        if add_organization_columns(engine):
            results["organization_columns"] = "added"
        else:
            results["organization_columns"] = "failed"
            return {"status": "error", "results": results}

        # Step 3: Populate organizations from existing data
        if populate_organizations(engine):
            results["organizations_populated"] = "success"
        else:
            results["organizations_populated"] = "failed"
            return {"status": "error", "results": results}

        # Step 4: Verify migration
        if verify_migration(engine):
            results["migration_verified"] = "success"
        else:
            results["migration_verified"] = "failed"

        return {
            "status": "success",
            "message": "Organizations migration completed successfully!",
            "results": results
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Organizations migration failed: {str(e)}",
            "error": str(e)
        }

@router.post("/add-missing-user-columns")
async def add_missing_user_columns(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Add missing user columns that were not included in the original migration.
    Fixes: column users.joined_org_at does not exist
    """

    # Security check: Only admins can run migrations
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    try:
        from sqlalchemy import text

        add_columns_sql = """
        -- Add missing user columns
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS joined_org_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS last_active_at TIMESTAMP WITH TIME ZONE,
        ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';

        -- Create indexes
        CREATE INDEX IF NOT EXISTS idx_users_joined_org_at ON users(joined_org_at);
        CREATE INDEX IF NOT EXISTS idx_users_last_active_at ON users(last_active_at);
        CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
        """

        db.execute(text(add_columns_sql))
        db.commit()

        return {
            "status": "success",
            "message": "Successfully added missing user columns",
            "columns_added": ["joined_org_at", "last_active_at", "status"]
        }

    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to add missing user columns: {str(e)}",
            "error": str(e)
        }


@router.post("/refresh-demo-analyses")
@limiter.limit("5/minute")
async def refresh_demo_analyses(
    request: Request,
    x_admin_api_key: str = Header(None, alias="X-Admin-API-Key"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Refresh all demo analyses with the latest mock data.

    This endpoint updates existing demo analyses and creates new ones for users
    who don't have a demo analysis. Use this after updating mock_analysis_data.json
    with new fields or data.

    Security: Requires BOTH admin role AND valid API key (defense-in-depth).
    Optional IP whitelist can be configured via ADMIN_IP_WHITELIST env var.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Security Layer 1: Validate API key is properly configured
    if not _admin_api_key_valid:
        logger.warning(
            f"ADMIN AUDIT: Rejected request - API key not configured or invalid. "
            f"IP: {client_ip}, User: {current_user.id}"
        )
        raise HTTPException(status_code=503, detail="Admin endpoint temporarily unavailable")

    # Security Layer 2: IP whitelist check (if configured)
    if not _is_ip_whitelisted(client_ip, _ip_whitelist):
        logger.warning(
            f"ADMIN AUDIT: Rejected request - IP not whitelisted. "
            f"IP: {client_ip}, User: {current_user.id}"
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    # Security Layer 3: Verify admin role (defense-in-depth)
    if current_user.role != 'admin':
        logger.warning(
            f"ADMIN AUDIT: Rejected request - User lacks admin role. "
            f"IP: {client_ip}, User: {current_user.id}, Role: {current_user.role}"
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    # Security Layer 4: Validate API key with constant-time comparison
    if not secrets.compare_digest(x_admin_api_key or "", ADMIN_API_KEY):
        logger.warning(
            f"ADMIN AUDIT: Rejected request - Invalid API key. "
            f"IP: {client_ip}, User: {current_user.id}"
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    logger.info(
        f"ADMIN AUDIT: Authorized access to /refresh-demo-analyses. "
        f"IP: {client_ip}, User: {current_user.id}"
    )

    try:
        # Load mock data
        backend_dir = Path(__file__).parent.parent.parent.parent
        mock_data_path = backend_dir / "mock_analysis_data.json"

        if not mock_data_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Mock data file not found: {mock_data_path}"
            )

        with open(mock_data_path, 'r', encoding='utf-8') as f:
            mock_data = json.load(f)

        original_analysis = mock_data.get('analysis', {})
        new_results = original_analysis.get('results')

        if not new_results:
            raise HTTPException(
                status_code=500,
                detail="Mock data file is missing 'analysis.results'"
            )

        # Get all demo analyses
        all_analyses = db.query(Analysis).all()
        demo_analyses = [
            a for a in all_analyses
            if a.config and isinstance(a.config, dict) and a.config.get('is_demo') is True
        ]

        updated_count = 0
        created_count = 0
        errors = []

        # Update existing demo analyses
        for analysis in demo_analyses:
            try:
                analysis.results = new_results
                config = analysis.config.copy() if analysis.config else {}
                config['demo_updated_at'] = datetime.now().isoformat()
                analysis.config = config
                updated_count += 1
            except Exception as e:
                errors.append(f"Failed to update analysis #{analysis.id}: {str(e)}")

        # Create demo analyses for users who don't have one
        users = db.query(User).all()
        users_with_demo = {a.user_id for a in demo_analyses}

        for user in users:
            if user.id not in users_with_demo:
                try:
                    config = original_analysis.get('config', {}).copy()
                    config['is_demo'] = True
                    config['demo_created_at'] = datetime.now().isoformat()

                    new_analysis = Analysis(
                        user_id=user.id,
                        organization_id=getattr(user, 'organization_id', None),
                        rootly_integration_id=None,
                        integration_name="Demo Analysis",
                        platform=original_analysis.get('platform', 'rootly'),
                        time_range=original_analysis.get('time_range', 30),
                        status="completed",
                        config=config,
                        results=new_results,
                        error_message=None,
                        completed_at=datetime.now()
                    )
                    db.add(new_analysis)
                    created_count += 1
                except Exception as e:
                    errors.append(f"Failed to create demo for user #{user.id}: {str(e)}")

        db.commit()

        logger.info(
            f"ADMIN AUDIT: /refresh-demo-analyses completed successfully. "
            f"IP: {client_ip}, User: {current_user.id}, "
            f"Updated: {updated_count}, Created: {created_count}"
        )

        return {
            "status": "success",
            "message": "Demo analyses refreshed successfully",
            "updated_count": updated_count,
            "created_count": created_count,
            "total_demo_analyses": updated_count + created_count,
            "errors": errors or None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(
            f"ADMIN AUDIT: /refresh-demo-analyses failed. "
            f"IP: {client_ip}, User: {current_user.id}, "
            f"Error: {str(e)}"
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to refresh demo analyses"
        )