-- Migration: Add performance indexes for slow queries
-- Description: Adds missing indexes to analyses, integration_mappings, user_notifications, and rootly_integrations tables
-- Performance impact: Critical - analyses table queries taking 24s without proper indexes

-- ============================================================================
-- Analysis table (MOST CRITICAL - causing 24s queries)
-- ============================================================================
CREATE INDEX IF NOT EXISTS ix_analyses_user_id ON analyses(user_id);
CREATE INDEX IF NOT EXISTS ix_analyses_organization_id ON analyses(organization_id);
CREATE INDEX IF NOT EXISTS ix_analyses_status ON analyses(status);
CREATE INDEX IF NOT EXISTS ix_analyses_created_at ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS ix_analyses_user_status ON analyses(user_id, status);

-- ============================================================================
-- IntegrationMapping table
-- ============================================================================
CREATE INDEX IF NOT EXISTS ix_integration_mappings_user_id ON integration_mappings(user_id);
CREATE INDEX IF NOT EXISTS ix_integration_mappings_organization_id ON integration_mappings(organization_id);
CREATE INDEX IF NOT EXISTS ix_integration_mappings_analysis_id ON integration_mappings(analysis_id);
CREATE INDEX IF NOT EXISTS ix_integration_mappings_target_platform ON integration_mappings(target_platform);
CREATE INDEX IF NOT EXISTS ix_integration_mappings_user_platform ON integration_mappings(user_id, target_platform);
CREATE INDEX IF NOT EXISTS ix_integration_mappings_created_at ON integration_mappings(created_at DESC);

-- ============================================================================
-- UserNotification table
-- ============================================================================
CREATE INDEX IF NOT EXISTS ix_user_notifications_user_id ON user_notifications(user_id);
CREATE INDEX IF NOT EXISTS ix_user_notifications_email ON user_notifications(email);
CREATE INDEX IF NOT EXISTS ix_user_notifications_status ON user_notifications(status);
CREATE INDEX IF NOT EXISTS ix_user_notifications_organization_id ON user_notifications(organization_id);
CREATE INDEX IF NOT EXISTS ix_user_notifications_user_status ON user_notifications(user_id, status);
CREATE INDEX IF NOT EXISTS ix_user_notifications_created_at ON user_notifications(created_at DESC);

-- ============================================================================
-- RootlyIntegration table
-- ============================================================================
CREATE INDEX IF NOT EXISTS ix_rootly_integrations_user_id ON rootly_integrations(user_id);
CREATE INDEX IF NOT EXISTS ix_rootly_integrations_platform ON rootly_integrations(platform);
CREATE INDEX IF NOT EXISTS ix_rootly_integrations_user_platform ON rootly_integrations(user_id, platform);
