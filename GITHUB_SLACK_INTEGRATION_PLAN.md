# GitHub and Slack Integration Plan

## Overview
This plan outlines the integration of GitHub and Slack data collection into the existing Rootly burnout detector web application. The integration is based on the proven CLI implementation and follows the Christina Maslach Burnout Inventory methodology.

## Architecture Overview
The CLI implementation demonstrates a multi-platform approach with:
- **GitHub integration**: Collects commit patterns, PR activity, after-hours coding, and repository switching
- **Slack integration**: Analyzes communication patterns, sentiment, stress indicators, and after-hours messaging
- **Burnout Analysis**: Combines all data sources with weighted scoring (70% incidents, 15% GitHub, 15% Slack)

## Implementation Phases

### Phase 1: Database Schema & Core Models

#### Database Schema Extensions
```sql
-- GitHub integrations
CREATE TABLE github_integrations (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    github_token VARCHAR(255) ENCRYPTED,
    github_username VARCHAR(100),
    organizations TEXT[], -- JSON array of orgs
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Slack integrations  
CREATE TABLE slack_integrations (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    slack_token VARCHAR(255) ENCRYPTED,
    slack_user_id VARCHAR(20),
    workspace_id VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- User correlations across platforms
CREATE TABLE user_correlations (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    email VARCHAR(255),
    github_username VARCHAR(100),
    slack_user_id VARCHAR(20),
    rootly_email VARCHAR(255),
    pagerduty_user_id VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### Backend Models
- `backend/app/models/github_integration.py`
- `backend/app/models/slack_integration.py`  
- `backend/app/models/user_correlation.py`

### Phase 2: OAuth Integration & Authentication

#### Backend API Endpoints
**GitHub Integration:**
- `POST /api/github/connect` - OAuth flow initiation
- `GET /api/github/callback` - OAuth callback handler
- `POST /api/github/test` - Test GitHub token permissions
- `DELETE /api/github/disconnect` - Remove GitHub integration

**Slack Integration:**
- `POST /api/slack/connect` - OAuth flow initiation  
- `GET /api/slack/callback` - OAuth callback handler
- `POST /api/slack/test` - Test Slack token permissions
- `DELETE /api/slack/disconnect` - Remove Slack integration

#### OAuth Flow Implementation
**GitHub OAuth:**
1. User clicks "Connect GitHub" 
2. Redirect to GitHub OAuth with scopes: `repo`, `read:user`, `read:org`
3. Handle callback and store encrypted token
4. Fetch user profile and repository access
5. Test permissions and show success/error state

**Slack OAuth:**
1. User clicks "Connect Slack"
2. Redirect to Slack OAuth with scopes: `channels:history`, `groups:history`, `users:read`
3. Handle callback and store encrypted token
4. Test workspace access and user permissions
5. Show connected workspace and user info

### Phase 3: Data Collection Services

#### GitHub Collector (`/backend/app/services/github_collector.py`)
Based on existing CLI implementation:
- Migrate existing `GitHubCollector` class
- Add OAuth token management
- Implement rate limiting and caching
- Collect: commits, PRs, reviews, issues, after-hours activity

**Key Metrics:**
- Total commits/PRs/issues
- After-hours coding percentage
- Weekend coding percentage  
- Repository switching patterns
- Commit clustering (stress indicator)
- PR collaboration ratios

#### Slack Collector (`/backend/app/services/slack_collector.py`)
Based on existing CLI implementation:
- Migrate existing `SlackCollector` class
- Add OAuth token management
- Implement sentiment analysis with `vaderSentiment`
- Collect: messages, DMs, after-hours activity, stress indicators

**Key Metrics:**
- Message volume and patterns
- After-hours communication
- Sentiment analysis and volatility
- Stress indicator detection
- Channel diversity
- Response pattern analysis

### Phase 4: Enhanced Burnout Analysis

#### Multi-Platform Analyzer (`/backend/app/services/multi_platform_analyzer.py`)
- Extend existing burnout calculation
- Implement weighted scoring:
  - Rootly/PagerDuty: 70% (base incident data)
  - GitHub: 15% (coding patterns)
  - Slack: 15% (communication patterns)
- Calculate three Maslach dimensions across all platforms:
  - **Emotional Exhaustion**: Workload + after-hours activity
  - **Depersonalization**: Collaboration patterns + communication quality
  - **Personal Accomplishment**: Resolution success + productive output

#### User Correlation System
**Email Matching Logic:**
- Automatically correlate users across platforms by email
- Handle multiple emails per GitHub account
- Support manual user mapping overrides
- Implement fuzzy matching for similar email patterns

### Phase 5: Frontend Integration

#### New Setup Pages
- `/frontend/src/app/setup/github/page.tsx` - GitHub OAuth flow
- `/frontend/src/app/setup/slack/page.tsx` - Slack OAuth flow  
- Enhanced `/frontend/src/app/integrations/page.tsx` - Show all connected platforms

#### Enhanced Dashboard
- Enhanced `/frontend/src/app/dashboard/page.tsx` - Multi-platform burnout scores
- New charts for GitHub activity patterns
- New charts for Slack communication patterns
- Combined risk assessment visualization

#### Integration Components
- GitHub connection status and metrics
- Slack workspace connection and activity
- Multi-platform correlation indicators
- Enhanced burnout score breakdowns

### Phase 6: Configuration & Advanced Features

#### Analysis Configuration
- Business hours (9-17 default)
- Severity weights for different activities
- Threshold settings for risk levels
- Custom organization/workspace filtering

#### Mock Data Support
- Development mode with mock GitHub/Slack data
- Test user profiles with different risk levels
- Staging environment support

## Security Considerations

- **Token Encryption**: All API tokens encrypted in database
- **Token Rotation**: Implement token refresh mechanisms
- **Permission Validation**: Validate permissions before data collection
- **Rate Limiting**: Implement API rate limiting
- **Audit Logging**: Log all integration actions

## Key Integration Points

### Existing Codebase Integration
- Extend existing `Analysis` model to include GitHub/Slack data
- Update `BurnoutAnalyzer` to handle multi-platform inputs
- Enhance dashboard visualizations for combined metrics
- Add platform indicators to user interface

### Data Flow
1. User connects GitHub/Slack via OAuth
2. System establishes user correlations by email
3. Background jobs collect activity data
4. Multi-platform analyzer combines all data sources
5. Enhanced burnout scores displayed in dashboard

## Testing Strategy

### Unit Tests
- OAuth flow handling
- Data collection services
- Multi-platform analysis calculations
- User correlation logic

### Integration Tests
- End-to-end OAuth flows
- API endpoint functionality
- Database operations
- Frontend component interactions

### Mock Data Testing
- GitHub activity patterns
- Slack communication scenarios
- Multi-platform correlation cases
- Edge cases and error handling

## Development Workflow

1. **Phase 1**: Database schema and core models
2. **Phase 2**: OAuth integration and authentication
3. **Phase 3**: Data collection services
4. **Phase 4**: Enhanced analysis engine
5. **Phase 5**: Frontend integration
6. **Phase 6**: Configuration and advanced features

Each phase should be developed, tested, and deployed incrementally to ensure stability and maintainability.

## Success Metrics

- Successful OAuth connection rates
- Data collection accuracy and completeness
- Multi-platform analysis correlation accuracy
- User engagement with enhanced features
- Improved burnout prediction accuracy with additional data sources

## Configuration Reference

Based on CLI implementation (`config/config.json`):
- GitHub organizations to monitor
- Slack workspace settings
- User mapping configurations
- Analysis thresholds and weights
- Business hours and timezone settings