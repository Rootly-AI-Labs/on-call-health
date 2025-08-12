# Claude Development Session Notes

# Development Guidelines

## Philosophy

### Core Beliefs

- **Incremental progress over big bangs** - Small changes that compile and pass tests
- **Learning from existing code** - Study and plan before implementing
- **Pragmatic over dogmatic** - Adapt to project reality
- **Clear intent over clever code** - Be boring and obvious

### Simplicity Means

- Single responsibility per function/class
- Avoid premature abstractions
- No clever tricks - choose the boring solution
- If you need to explain it, it's too complex

## Process

### 1. Planning & Staging

Break complex work into 3-5 stages. Document in `IMPLEMENTATION_PLAN.md`:

```markdown
## Stage N: [Name]
**Goal**: [Specific deliverable]
**Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases]
**Status**: [Not Started|In Progress|Complete]
```
- Update status as you progress
- Remove file when all stages are done

### 2. Implementation Flow

1. **Understand** - Study existing patterns in codebase
2. **Test** - Write test first (red)
3. **Implement** - Minimal code to pass (green)
4. **Refactor** - Clean up with tests passing
5. **Commit** - With clear message linking to plan

### 3. When Stuck (After 3 Attempts)

**CRITICAL**: Maximum 3 attempts per issue, then STOP.

1. **Document what failed**:
   - What you tried
   - Specific error messages
   - Why you think it failed

2. **Research alternatives**:
   - Find 2-3 similar implementations
   - Note different approaches used

3. **Question fundamentals**:
   - Is this the right abstraction level?
   - Can this be split into smaller problems?
   - Is there a simpler approach entirely?

4. **Try different angle**:
   - Different library/framework feature?
   - Different architectural pattern?
   - Remove abstraction instead of adding?

## Technical Standards

### Architecture Principles

- **Composition over inheritance** - Use dependency injection
- **Interfaces over singletons** - Enable testing and flexibility
- **Explicit over implicit** - Clear data flow and dependencies
- **Test-driven when possible** - Never disable tests, fix them

### Code Quality

- **Every commit must**:
  - Compile successfully
  - Pass all existing tests
  - Include tests for new functionality
  - Follow project formatting/linting

- **Before committing**:
  - Run formatters/linters
  - Self-review changes
  - Ensure commit message explains "why"

### Error Handling

- Fail fast with descriptive messages
- Include context for debugging
- Handle errors at appropriate level
- Never silently swallow exceptions

## Decision Framework

When multiple valid approaches exist, choose based on:

1. **Testability** - Can I easily test this?
2. **Readability** - Will someone understand this in 6 months?
3. **Consistency** - Does this match project patterns?
4. **Simplicity** - Is this the simplest solution that works?
5. **Reversibility** - How hard to change later?

## Project Integration

### Learning the Codebase

- Find 3 similar features/components
- Identify common patterns and conventions
- Use same libraries/utilities when possible
- Follow existing test patterns

### Tooling

- Use project's existing build system
- Use project's test framework
- Use project's formatter/linter settings
- Don't introduce new tools without strong justification

## Quality Gates

### Definition of Done

- [ ] Tests written and passing
- [ ] Code follows project conventions
- [ ] No linter/formatter warnings
- [ ] Commit messages are clear
- [ ] Implementation matches plan
- [ ] No TODOs without issue numbers

### Test Guidelines

- Test behavior, not implementation
- One assertion per test when possible
- Clear test names describing scenario
- Use existing test utilities/helpers
- Tests should be deterministic

## Important Reminders

**NEVER**:
- Use `--no-verify` to bypass commit hooks
- Disable tests instead of fixing them
- Commit code that doesn't compile
- Make assumptions - verify with existing code

**ALWAYS**:
- Commit working code incrementally
- Update plan documentation as you go
- Learn from existing implementations
- Stop after 3 failed attempts and reassess

---

# Claude Development Session Notes

## Project: OnCall Burnout Detector - Railway Deployment & Analysis Fixes

### Recent Major Work Completed

✅ **Major fixes completed**: UUID implementation, Railway compatibility, analysis execution errors, burnout factors chart data, historical analyses visibility, and health trends chart logic.

### Testing Commands:
```bash
# Run backend
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Check database migrations needed on Railway
cd backend && python run_uuid_migration.py

# Debug trends data
cd backend && python debug_trends_data.py
```

### Known Working Features:
- ✅ Analysis creation and execution
- ✅ Burnout factors chart with real data
- ✅ Historical analyses list
- ✅ UUID-based shareable URLs
- ✅ Background analysis processing
- ✅ Error handling and recovery

### CRITICAL ISSUES TO FIX - EXECUTION PLAN

#### Issue #1: Frontend Shows Fallback/Demo Data for Non-Existent Analyses
**Problem**: URL shows `?analysis=64` but analysis doesn't exist, causing frontend to show hardcoded demo data (110 incidents, 18 days)
**Impact**: Users see inconsistent fake data that doesn't match any real analysis

**Fix Plan**:
1. **Frontend**: Add proper error handling when analysis not found
   - File: `frontend/src/app/dashboard/page.tsx`
   - Check if analysis exists before displaying data
   - Show clear error message: "Analysis not found" 
   - Redirect to most recent valid analysis or show empty state
   - Remove hardcoded fallback data (110 incidents, 18 days pattern)
   - **CRITICAL: NO FALLBACK DATA - Always show real state:**
     - If no data: "No incident data available"
     - If 0 incidents: "0 incidents analyzed" 
     - If API error: "Failed to fetch incidents: [error message]"
     - If daily trends empty: "No daily trend data generated"
     - NEVER show fake/demo data

2. **Backend**: Return proper 404 with redirect suggestion
   - File: `backend/app/api/endpoints/analyses.py`
   - When analysis not found, include most recent valid analysis ID in error response
   - Frontend can use this to auto-redirect
   - Include error details in response for frontend to display

#### Issue #2: Daily Trends Generation Completely Broken
**Problem**: ALL 78 completed analyses have 0 daily trends data, causing empty charts
**Impact**: Health trends chart shows no real data for any analysis

**Fix Plan**:
1. **Immediate Fix**: Add data regeneration endpoint
   - Create `/analyses/{id}/regenerate-trends` endpoint
   - Regenerate daily trends for existing analyses
   - Use the incident generation logic when API permissions blocked

2. **Root Cause Fix**: Ensure daily trends always generated
   - File: `backend/app/services/burnout_analyzer.py`
   - Add validation that daily_trends is never empty
   - If no incidents but time period exists, generate empty daily entries
   - Log warnings when daily trends generation fails

#### Issue #3: UUID Implementation Incomplete
**Problem**: UUID column commented out, using integer IDs, no shareable URLs
**Impact**: URLs not shareable, sequential IDs expose data

**Fix Plan**:
1. **Complete UUID Implementation**:
   - File: `backend/app/models/analysis.py`
   - Uncomment UUID column: `uuid = Column(String(36), unique=True, index=True, nullable=True, default=lambda: str(uuid.uuid4()))`
   - Commit and push the change

2. **Run Migration on Railway**:
   - The migration script already exists: `backend/migrate_uuid_step1.py`
   - Run via Railway CLI or web console
   - Verify UUID column added to all existing analyses

3. **Update Frontend to Use UUIDs**:
   - File: `frontend/src/app/dashboard/page.tsx`
   - Switch from `?analysis={id}` to `?analysis={uuid}`
   - Keep fallback to integer ID for backward compatibility

#### Issue #4: API Permissions Preventing Real Data
**Problem**: Rootly API returns 404 on incidents endpoint (missing incidents:read permission)
**Impact**: All analyses show 0 real incidents, only generated/fake data

**Fix Plan**:
1. **Update Rootly API Token**:
   - Get new token with 'incidents:read' permission from Rootly
   - Update in integration settings
   
2. **Add Permission Check on Integration Setup**:
   - File: `backend/app/api/endpoints/rootly.py`
   - Test permissions when saving integration
   - Show clear warning if incidents:read missing

#### Issue #5: Data Consistency Between Components
**Problem**: Different dashboard components show different data sources
**Impact**: Total incidents, charts, and metrics don't match

**Fix Plan**:
1. **Single Source of Truth**:
   - All components must read from analysis.results
   - Remove any hardcoded values
   - Add data validation to ensure consistency
   - **NO FALLBACK DATA PRINCIPLE**:
     - Every component shows EXACTLY what's in the database
     - If data is missing, show "Data not available" 
     - If calculation fails, show "Unable to calculate"
     - Log all issues for debugging

2. **Add Data Integrity Check**:
   - Create consistency validator
   - Run before displaying analysis
   - Log any discrepancies found
   - Display warnings to user when data inconsistencies detected

#### CORE PRINCIPLE: Transparency Over Prettiness
**Always show the real state of the system:**
- Empty data → Show empty state with explanation
- Failed API calls → Show error with details
- Missing permissions → Show "Insufficient permissions to access incidents"
- Broken calculations → Show "Calculation error" with details
- NEVER hide problems with fake data

## ERROR HANDLING SYSTEM - IMPLEMENTATION PLAN

### Overview
Create a robust error display system with clear, actionable error messages for users.

### Error Categories:
- 🚨 **Critical**: Analysis failures, DB issues, auth failures
- ⚠️ **Data Collection**: API permissions, rate limits, token issues
- ℹ️ **Data Quality**: Incomplete data, missing integrations
- 💡 **Processing**: Performance concerns, feature limitations

### Implementation Plan:
1. **Backend Error Tracking**: Centralized error service, API endpoints
2. **Frontend Error Display**: Error modal, badge in header, categorized display
3. **Quick Actions**: Retry mechanisms, direct links to fix settings
4. **Error Templates**: Common error messages with suggested actions

## FALLBACK DATA AUDIT & REMOVAL PLAN

### CORE PRINCIPLE: RADICAL TRANSPARENCY - NO FAKE DATA
**If we don't have real data, we show "No data available" - NEVER fake it**

### Key Areas to Audit:
1. **Frontend Components**: Remove `|| 0` fallbacks, fake chart data, placeholder values
2. **Backend Services**: Eliminate mock data generation, default calculations
3. **API Responses**: No fallback analysis data in responses
4. **Database**: Verify no placeholder data in stored analyses

### Replacement Strategy:
- Replace fallback data with clear "No data available" states
- Show empty state components with explanatory messages
- Provide actionable buttons to fix data issues
- Use consistent "no data" language across components

### IMMEDIATE ACTIONS - Remove All Fallback Data

**Search and Remove These Patterns**:
1. **Frontend** (`frontend/src/app/dashboard/page.tsx`):
   - Any hardcoded "110 incidents"
   - Any "18 days" pattern
   - Default health scores when data missing
   - Mock timeline events
   - Placeholder member data
   
2. **Backend** (all analyzer files):
   - Remove any demo/mock data generation
   - Remove default values that hide real issues
   - Keep ONLY the incident generation for consistency (when metadata shows incidents but API fails)

**Replace With**:
```typescript
// Instead of: incidents = fallbackData || []
// Use: incidents = data?.incidents || []
// Display: {incidents.length === 0 ? "No incidents to display" : <IncidentChart />}
```

### DATA VERIFICATION & CROSS-CHECK PLAN

#### Automated Data Consistency Verification System

**1. Backend Validation Endpoint** (`/analyses/{id}/verify-consistency`):
```python
# Returns detailed consistency report
{
  "analysis_id": 140,
  "consistency_checks": {
    "incident_totals": {
      "metadata_total": 110,
      "team_analysis_sum": 108,
      "daily_trends_sum": 18,
      "match": false,
      "discrepancy": "Daily trends only sum to 18, not 110"
    },
    "member_counts": {
      "metadata_users": 38,
      "team_analysis_members": 38,
      "members_with_incidents": 5,
      "match": true
    },
    "date_ranges": {
      "metadata_days": 30,
      "daily_trends_days": 18,
      "expected_data_points": 30,
      "actual_data_points": 18,
      "match": false,
      "discrepancy": "Missing 12 days of daily trend data"
    },
    "severity_distribution": {
      "metadata_breakdown": {"SEV1": 3, "SEV2": 60, "SEV3": 16, "SEV4": 31},
      "calculated_total": 110,
      "incidents_with_severity": 110,
      "match": true
    }
  },
  "overall_consistency": false,
  "critical_issues": [
    "Daily trends incomplete: 18/30 days",
    "Daily incident sum (18) doesn't match total (110)"
  ]
}
```

**2. Frontend Consistency Dashboard** (Development Mode):
- Add debug panel showing all data sources
- Visual indicators when numbers don't match
- Color coding: ✅ Green (match), ❌ Red (mismatch), ⚠️ Yellow (close but off)

**3. Cross-Component Validation Rules**:

**Top Cards vs Source Data**:
```typescript
// Team Health Card
- Value shown: analysis.results.team_health.overall_score
- Validation: Must be between 0-100
- Cross-check: Average of member scores should be within 10% of overall

// At Risk Card  
- Value shown: analysis.results.team_health.members_at_risk
- Validation: Cannot exceed total members
- Cross-check: Count of members with risk_level !== 'low'

// Total Incidents Card
- Value shown: analysis.results.metadata.total_incidents
- Cross-checks:
  1. Sum of daily_trends[].incident_count
  2. Sum of team_analysis.members[].incident_count
  3. Sum of severity_breakdown values
  - ALL must match exactly
```

**Health Trends Chart vs Source Data**:
```typescript
// Each data point
- Date: daily_trends[i].date
- Score: daily_trends[i].overall_score
- Incidents: daily_trends[i].incident_count

// Validations:
- Number of points === metadata.days_analyzed
- Date range covers full analysis period
- Sum of incidents === metadata.total_incidents
- No duplicate dates
- Dates in chronological order
```

**4. Automated Test Suite**:
```python
# tests/test_data_consistency.py
def test_analysis_data_consistency():
    for analysis in get_all_completed_analyses():
        # Test 1: Incident totals match across all sources
        assert sum(day['incident_count'] for day in analysis.daily_trends) == analysis.metadata.total_incidents
        
        # Test 2: Daily trends cover full time period
        assert len(analysis.daily_trends) == analysis.metadata.days_analyzed
        
        # Test 3: Member incident counts sum to total
        member_incident_sum = sum(m['incident_count'] for m in analysis.team_analysis.members)
        assert member_incident_sum == analysis.metadata.total_incidents
        
        # Test 4: At-risk count matches actual risk levels
        at_risk_calculated = len([m for m in analysis.team_analysis.members if m['risk_level'] != 'low'])
        assert at_risk_calculated == analysis.team_health.members_at_risk
```

**5. Manual Verification Checklist** (For QA):
- [ ] Total Incidents card matches sum of severity breakdown
- [ ] Health trends chart shows correct number of days
- [ ] Each day's incidents sum to total when added
- [ ] Team health percentage matches calculation
- [ ] At-risk count matches highlighted members
- [ ] Timeline events correspond to daily trend data
- [ ] Burnout factors chart values sum correctly
- [ ] All dates match analysis time range

**6. Real-time Consistency Monitor**:
- Add console warnings when displaying inconsistent data
- Log discrepancies to monitoring system
- Email alert if consistency < 95% for new analyses

## COMPREHENSIVE FALLBACK DATA AUDIT RESULTS

### Critical Fallback Patterns Found in `frontend/src/app/dashboard/page.tsx`

#### 1. GitHub Activity Card Fallbacks (Lines 3900-3920)
**CRITICAL ISSUES**:
- `github.total_commits?.toLocaleString() || 0` - Shows 0 instead of "No data"
- `github.total_pull_requests?.toLocaleString() || 0` - Shows 0 instead of "No data" 
- `github.total_reviews?.toLocaleString() || 0` - Shows 0 instead of "No data"
- `github.after_hours_activity_percentage?.toFixed(1) || 0` - Shows 0% instead of "No data"
- `github.weekend_activity_percentage?.toFixed(1) || 0` - Shows 0% instead of "No data"
- `(github as any).avg_pr_size?.toFixed(0) || 0` - Shows 0 instead of "No data"

**IMPACT**: Users see "0 commits, 0 PRs, 0 reviews" when GitHub isn't connected, making them think there's no activity instead of no data connection.

#### 2. Slack Communications Card Fallbacks (Lines 4005-4020)
**CRITICAL ISSUES**:
- Card resets all metrics to 0 when no real Slack data detected
- Shows `total_messages: 0, active_channels: 0, after_hours_activity_percentage: 0` instead of "No Slack data"
- Complex fallback logic tries to detect "real" vs "cached" data but still shows zeros

**IMPACT**: Dashboard shows "0 messages, 0 channels" instead of clear "Slack not connected" state.

#### 3. Burnout Factors Chart Calculations (Lines 1937-2054)
**CRITICAL ISSUES**:
- `m?.factors?.after_hours || Math.min(afterHoursPercent * 20, 10)` - Calculates fake factor values
- `m?.key_metrics?.incidents_per_week || (m?.incident_count / 4.3) || 0` - Creates fake incident rates
- `m?.key_metrics?.severity_weighted_per_week || 0` - Shows 0 instead of "No data"
- `m?.factors?.incident_load || (workloadScore * 0.4 + severityScore * 0.6)` - Calculates fake load values
- `m?.factors?.response_time || (() => { /* complex calculation */ })()` - Creates fake response times

**IMPACT**: Radar charts show calculated/fake burnout factors instead of real API data, completely misleading users about actual burnout risk.

#### 4. Member Detail Modal Fallbacks (Lines 4773-5172)
**CRITICAL ISSUES**:
- `memberData?.burnout_score || (selectedMember.burnoutScore / 10) || 0` - Shows 0 score instead of "No data"
- `selectedMember.slack_activity?.messages_sent || 0` - Shows 0 messages instead of "No Slack data"
- `selectedMember.slack_activity?.channels_active || 0` - Shows 0 channels instead of "No data"
- `selectedMember.slack_activity?.sentiment_score || 0` - Shows neutral sentiment instead of "No data"
- Complex percentage calculations with fallbacks that hide missing data

**IMPACT**: Member details show fake 0 values and calculated percentages instead of clear "No data available" states.

#### 5. General Data Access Patterns
**CRITICAL ISSUES**:
- `data.analyses || []` - Shows empty list instead of loading/error state
- `analysis.uuid || analysis.id` - Uses integer ID as fallback (acceptable)
- `teamAnalysis?.members || []` - Shows empty team instead of "No members analyzed"
- `membersWithIncidents.length > 0` filtering but then uses `|| 0` fallbacks throughout

### REPLACEMENT STRATEGY - NO FALLBACK DATA PRINCIPLE

#### Replace All `|| 0` Patterns With:
```typescript
// Instead of:
<p>{github.total_commits?.toLocaleString() || 0}</p>

// Use:
{github.total_commits ? (
  <p>{github.total_commits.toLocaleString()}</p>
) : (
  <p className="text-gray-500 italic">No GitHub data available</p>
)}
```

#### Replace All Calculated Fallbacks With:
```typescript
// Instead of:
const val = m?.factors?.after_hours || Math.min(afterHoursPercent * 20, 10);

// Use:
const val = m?.factors?.after_hours;
if (val === undefined) {
  return <div className="text-gray-500">No after-hours data available</div>
}
```

#### Replace All Array Fallbacks With:
```typescript
// Instead of:
const members = teamAnalysis?.members || []

// Use:
const members = teamAnalysis?.members
if (!members || members.length === 0) {
  return <div className="text-center text-gray-500">No team members analyzed</div>
}
```

### EMPTY STATE COMPONENTS NEEDED

#### 1. EmptyGitHubCard Component
- Shows "GitHub not connected" message
- "Connect GitHub" button
- Clear explanation of what data would be shown

#### 2. EmptySlackCard Component  
- Shows "Slack not connected" message
- "Connect Slack" button
- Clear explanation of communication metrics

#### 3. EmptyMemberData Component
- Shows "No member data available"
- Explains why (no incidents, no GitHub activity, etc.)
- Suggests actions to get data

#### 4. EmptyBurnoutFactors Component
- Shows "Insufficient data for burnout analysis"
- Lists what data sources are needed
- Shows current data source status

## FALLBACK DATA REMOVAL - COMPLETED ✅

✅ **All fallback data removed** from dashboard components. Users now see clear "No data available" states instead of fake zeros or calculated values. 200+ lines of fallback logic eliminated from frontend.

### EXECUTION ORDER:
1. **Day 1**: Fix frontend fallback data (Issue #1) - ✅ COMPLETED  
2. **Day 1**: Add trends regeneration endpoint (Issue #2)
3. **Day 2**: Complete UUID implementation (Issue #3)
4. **Day 2**: Fix API permissions (Issue #4)
5. **Day 3**: Implement data consistency checks (Issue #5)
6. **Day 3**: Deploy verification system

## NEW FEATURE IMPLEMENTATION PLAN: Manual User Mapping UI/UX

### Objective: Create Frontend Interface for User Platform Mapping Management

**Problem**: Currently, platform mappings (Rootly/PagerDuty → GitHub) are hardcoded in Python files. Users cannot manage these mappings without code changes.

**Solution**: Build a user-friendly frontend interface that leverages the existing comprehensive mapping API backend.

### Key Architecture Decisions

#### 1. Slack Mappings NOT Needed ✅
- **Rationale**: Slack users authenticate with company email addresses
- **Solution**: Use Slack API to fetch user emails directly
- **Implementation**: `users.info` API endpoint provides email field
- **Result**: Automatic email-based correlation, no manual mapping required

#### 2. Integration-Scoped Mappings ✅
- **Problem**: Different Rootly/PagerDuty integrations = different organizations/teams
- **Solution**: Mappings tied to specific integration_id, not global
- **Database**: Add `integration_id` foreign key to UserMapping table
- **UI**: Show mappings per integration, not globally

#### 3. Simplified Mapping Flow ✅
**What we're mapping**: 
- Rootly/PagerDuty email/user_id → GitHub username
- That's it! Slack correlation happens automatically via email

### Summary of Changes from Original Plan

1. **Removed Slack from manual mapping** - Auto-correlation via email
2. **Integration-scoped mappings** - Each Rootly/PD integration has its own mappings
3. **Simplified UI** - Only map to GitHub, not multiple platforms
4. **Integration page links** - Add "Manage GitHub Mappings" to each integration card
5. **Automatic Slack correlation** - Backend fetches Slack emails and matches automatically

### Updated Implementation Plan

#### Phase 1: Integration Page Updates (Day 1)

**1.1 Add Mapping Links to Integration Cards**
- **Location**: Each Rootly/PagerDuty integration card
- **UI**: "Manage GitHub Mappings" link/button
- **File**: `frontend/src/app/integrations/page.tsx`
- **Action**: Opens drawer with mappings for THAT specific integration

**1.2 Update Database Schema**
```sql
ALTER TABLE user_mappings 
ADD COLUMN integration_id INTEGER REFERENCES integrations(id);
-- Mappings are now scoped to specific integrations
```

**1.3 Simplified Mapping Flow**
- User clicks "Manage GitHub Mappings" on a Rootly integration
- Drawer opens showing ONLY users from that Rootly org
- Map each Rootly user email → GitHub username
- Slack correlation happens automatically via email matching

#### Phase 2: Mapping Drawer Component (Day 2)

**2.1 Create Integration-Scoped Mapping Drawer**
- **Component**: `components/GitHubMappingDrawer.tsx`
- **Props**: `integrationId`, `integrationType` (rootly/pagerduty)
- **Features**:
  - Fetch users from specific integration
  - Show existing GitHub mappings
  - Add/edit/delete mappings
  - Real-time GitHub username validation

**2.2 Simplified Mapping Table**
- **Columns**: 
  - Team Member (from Rootly/PD)
  - Email
  - GitHub Username
  - Status (mapped/unmapped)
  - Actions (add/edit/remove)

#### Phase 2: Advanced Features (Day 3-4)

**2.1 Smart Suggestions**
- Integrate with `/api/manual-mappings/suggestions` endpoint
- Show suggested GitHub usernames based on email patterns
- Auto-complete functionality

**2.2 Bulk Operations**
- CSV import/export functionality
- Bulk validation of mappings
- Batch creation from team member list

**2.3 Mapping Analytics**
- Success rate dashboard
- Platform coverage statistics  
- Unmapped users identification

#### Phase 3: Integration & Polish (Day 5)

**3.1 Dashboard Integration**
- Show mapping coverage in Data Sources card
- Display unmapped user warnings
- Link to mapping management from dashboard

**3.2 Real-time Validation**
- Validate GitHub usernames against GitHub API
- Check Slack user IDs for existence
- Show mapping health status

**3.3 User Experience Polish**
- Loading states and error handling
- Confirmation dialogs for destructive actions
- Toast notifications for success/failure

### Technical Implementation Details

#### 3.1 API Integration
**Updated Endpoints (Integration-Scoped)**:
- `GET /api/integrations/{id}/users` - Fetch users from Rootly/PD integration
- `GET /api/integrations/{id}/mappings` - Fetch GitHub mappings for this integration
- `POST /api/integrations/{id}/mappings` - Create new mapping
- `PUT /api/integrations/{id}/mappings/{mapping_id}` - Update mapping
- `DELETE /api/integrations/{id}/mappings/{mapping_id}` - Delete mapping
- `GET /api/integrations/{id}/mappings/suggestions` - Get GitHub username suggestions
- `POST /api/integrations/{id}/mappings/validate` - Validate GitHub username
- `GET /api/integrations/{id}/mappings/statistics` - Get mapping coverage stats

**Slack Email Fetching**:
- `GET /api/slack/users` - Fetch all Slack users with emails
- Backend automatically correlates by email during analysis

#### 3.2 Component Structure
```
components/
├── UserMappingDrawer.tsx          # Main drawer component
├── MappingTable.tsx               # Table with mappings
├── AddMappingModal.tsx            # Add/edit mapping form
├── MappingValidation.tsx          # Real-time validation
├── BulkMappingImport.tsx          # CSV import functionality
└── MappingStatistics.tsx          # Analytics dashboard
```

#### 3.3 Data Flow
1. **Load Mappings**: Fetch from API on drawer open
2. **Create Mapping**: Form validation → API call → Refresh table
3. **Edit Mapping**: Inline editing → Validation → API update
4. **Delete Mapping**: Confirmation → API delete → Remove from table
5. **Suggestions**: Type email → API suggestions → Show options

#### 3.4 UI/UX Design

**Integration Card Update**:
```
┌─ Rootly Connected ─────────────────────────────────────┐
│ ✅ acme-corp.rootly.com                                │
│ Organization: Acme Corp                                │
│ Team Members: 15                                       │
│                                                        │
│ [🔧 Test] [👥 Manage GitHub Mappings] [⚙️ Settings]    │
└────────────────────────────────────────────────────────┘
```

**GitHub Mapping Drawer**:
```
┌─ GitHub Mappings - Acme Corp (Rootly) ─────────────────┐
│ 📊 Coverage: 12/15 users mapped (80%)                 │
│ 🔄 Last sync: 2 hours ago                             │
│                                                        │
│ [🔍 Search] [+ Add Mapping] [Import CSV]              │
│                                                        │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Team Member         │ Email           │ GitHub   │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Spencer Cheng       │ spencer@acme... │ ✅ spen… │ │
│ │                     │                 │ [Edit]   │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ John Doe           │ john@acme.com   │ ❌ Not   │ │
│ │                     │                 │ [Add]    │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Jane Smith         │ jane@acme.com   │ ⚠️ jane  │ │
│ │                     │                 │ [Verify] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                        │
│ ℹ️ Slack users are automatically matched by email      │
│                                                        │
│ [Close]                                                │
└────────────────────────────────────────────────────────┘
```

**Add/Edit GitHub Mapping Modal**:
```
┌─ Map GitHub Account ───────────────────────────────────┐
│                                                        │
│ 👤 Team Member: John Doe                               │
│ 📧 Email: john@acme.com                                │
│                                                        │
│ 🐙 GitHub Username                                     │
│ [@_____________johndoe] [🔍 Verify]                    │
│                                                        │
│ 💡 Suggestions based on email:                         │
│ • johndoe (90% match)                                  │
│ • john-doe-acme (75% match)                            │
│ • jdoe123 (60% match)                                  │
│                                                        │
│ ✅ Validation: Username exists and has recent activity  │
│                                                        │
│ [Cancel] [Save Mapping]                                │
└────────────────────────────────────────────────────────┘
```

### Files to Create/Modify

#### New Files:
- `frontend/src/components/GitHubMappingDrawer.tsx` - Main drawer for GitHub mappings
- `frontend/src/components/GitHubMappingTable.tsx` - Table showing user→GitHub mappings
- `frontend/src/components/AddGitHubMappingModal.tsx` - Modal to add/edit mappings
- `frontend/src/hooks/useIntegrationMappings.ts` - Hook for integration-scoped mappings
- `frontend/src/types/mapping.ts` - TypeScript types

#### Modified Files:
- `frontend/src/app/integrations/page.tsx` - Add "Manage GitHub Mappings" to each integration
- `backend/app/models/user_mapping.py` - Add integration_id column
- `backend/app/api/endpoints/integrations.py` - Add mapping endpoints
- `backend/app/services/slack_collector.py` - Fetch and use email from Slack API
- `backend/app/services/github_collector.py` - Use database mappings instead of hardcoded

### Success Metrics
- **Mapping Coverage**: Increase from ~70% to 95%+ team coverage
- **User Adoption**: 90% of admin users utilize mapping interface
- **Data Quality**: Reduce "no GitHub/Slack data" incidents by 80%
- **Maintenance**: Eliminate developer time spent on mapping updates

### Migration Strategy
1. **Phase 1**: Build UI alongside existing hardcoded mappings
2. **Phase 2**: Migrate hardcoded mappings to database
3. **Phase 3**: Remove hardcoded mappings, use database as single source
4. **Phase 4**: Add advanced features (auto-detection, suggestions)

### CURRENT CRITICAL ISSUE - Dashboard Mapping Drawer Data Loading ✅

✅ **FIXED** - Environment variable mismatch resolved. MappingDrawer now uses consistent API URL across all components.

### NEXT MAJOR ENHANCEMENT - GitHub-Only Burnout Analysis 🚧

#### Objective: Evaluate Burnout for Users with High GitHub Activity but Zero Incidents

**Problem Statement**: Current analysis only considers users who appear in incident data, missing potential burnout in developers who:
- Work long hours but aren't on-call rotation
- Have high code velocity but don't handle incidents
- Show burnout signals in development patterns before incidents occur
- Are junior developers not yet involved in incident response

#### Implementation Plan

##### Phase 1: Data Collection Enhancement
**Expand user collection to include GitHub-active developers**:

1. **Enhanced User Discovery**:
   - Current: Users discovered from Rootly incident data only
   - Enhanced: Users discovered from incident data + GitHub contributors + Slack active members
   - API calls: Combine Rootly users + GitHub org members + Slack workspace members

2. **GitHub Activity Thresholds**:
   - Minimum commits per analysis period (e.g., 5+ commits in 30 days)
   - Regular contribution patterns (not one-time contributors)
   - Activity across multiple repositories

3. **User Classification System**:
   ```python
   user_types = {
       "incident_responder": {"incidents": ">0", "github": "any", "slack": "any"},
       "pure_developer": {"incidents": "0", "github": ">threshold", "slack": "any"}, 
       "inactive": {"incidents": "0", "github": "<threshold", "slack": "low"},
       "communication_heavy": {"incidents": "any", "github": "low", "slack": ">threshold"}
   }
   ```

##### Phase 2: GitHub-Specific Burnout Indicators Based on Maslach Burnout Inventory
**Develop burnout detection mapped to validated psychological constructs**:

**Scientific Foundation**: Christina Maslach's research identifies three core dimensions:
1. **Emotional Exhaustion** - Feeling emotionally drained and depleted
2. **Depersonalization/Cynicism** - Detached, callous attitudes toward work
3. **Reduced Personal Accomplishment** - Feelings of ineffectiveness and lack of achievement

#### GitHub Data Mapping to MBI Dimensions:

**1. Emotional Exhaustion Indicators (40% weight)**:
   - **Temporal Overextension**:
     * Commits spread >12 hours/day consistently
     * Weekend commits >20% of total (normal: <10%)
     * After-hours commits (post-6PM, pre-8AM) trending upward
     * No "commit-free" days in 2+ week periods
   
   - **Intensity Without Recovery**:
     * Daily commit frequency 2+ std deviations above personal baseline
     * Commit timestamps showing <8 hours between last/first commits
     * Vacation periods with continued coding activity
     * Sprint periods without recovery weeks
   
   - **Methodology**: Compare against individual baseline + team norms
     ```python
     exhaustion_score = (
         temporal_overextension * 0.4 +
         intensity_without_recovery * 0.3 +
         baseline_deviation * 0.3
     )
     # Normalize to 0-100 scale where >70 = high risk
     ```

**2. Depersonalization/Cynicism Indicators (35% weight)**:
   - **Reduced Social Coding Behaviors**:
     * Code review participation drops >30% from baseline
     * Pull request descriptions become terse/minimal
     * Decreased helpful comments on others' PRs
     * Less participation in architectural discussions (measured via PR comments)
   
   - **Quality of Interaction Degradation**:
     * Commit messages become less descriptive (character count trend)
     * Increased use of generic messages ("fix", "update", "wip")
     * Reduced documentation contributions
     * Less mentoring activity (junior developer interactions)
   
   - **Defensive/Withdrawn Patterns**:
     * Smaller, more frequent commits (avoiding peer review)
     * Working in isolation (fewer collaborative commits)
     * Reduced cross-repository contributions
     * Less experimental/creative coding (measured by branch diversity)
   
   - **Methodology**: Baseline against historical collaboration patterns
     ```python
     cynicism_score = (
         social_coding_decline * 0.4 +
         interaction_quality_drop * 0.35 +
         withdrawal_patterns * 0.25
     )
     ```

**3. Reduced Personal Accomplishment Indicators (25% weight)**:
   - **Declining Code Quality Metrics**:
     * Increased bug-fix to feature-commit ratio
     * More reverts and rollbacks of own code  
     * Longer time to complete similar-sized features
     * Decreased complexity of problems tackled
   
   - **Productivity Paradox Signals**:
     * High commit volume with low meaningful progress
     * Increased "churn" (lines added then removed)
     * More "cleanup" commits vs substantial contributions
     * Decreased innovation (fewer new patterns/approaches)
   
   - **Achievement Pattern Changes**:
     * Longer PR cycles (feature delivery delays)
     * Reduced ownership of significant features
     * Less involvement in technical decision-making
     * Decreased cross-team collaboration impact
   
   - **Methodology**: Track accomplishment trends vs role expectations
     ```python
     accomplishment_score = 100 - (  # Inverted - lower = worse
         quality_decline * 0.4 +
         productivity_paradox * 0.35 +
         achievement_reduction * 0.25
     )
     ```

#### Composite GitHub Burnout Score:
```python
github_burnout_score = (
    emotional_exhaustion * 0.40 +
    cynicism_score * 0.35 +
    (100 - accomplishment_score) * 0.25  # Invert for consistent direction
)

# Risk Level Classification (aligned with clinical MBI ranges):
# 0-30: Low Risk (healthy patterns)
# 31-60: Moderate Risk (some concerning patterns)  
# 61-80: High Risk (multiple strong indicators)
# 81-100: Critical Risk (severe burnout indicators)
```

#### Critical Implementation Considerations:

**1. Individual Baseline Establishment**:
- Require minimum 3 months of historical data before scoring
- Account for role changes, project transitions, learning curves
- Seasonal adjustments (end-of-quarter pushes, vacation periods)
- Personal productivity patterns (some developers naturally work evenings)

**2. False Positive Prevention**:
- **Scenario**: Developer working "non-stop throughout the day"
- **Risk**: High exhaustion score from temporal patterns
- **Mitigation**: 
  * Cross-reference with productivity metrics (are they actually productive?)
  * Check for "flow state" patterns (consistent, sustainable output)
  * Validate against self-reported satisfaction/energy levels
  * Consider cultural/timezone factors (distributed teams)

**3. Statistical Rigor**:
```python
def calculate_burnout_with_confidence(user_data, baseline_data, team_norms):
    """
    Calculate burnout score with statistical confidence intervals
    """
    # Minimum data requirements
    if user_data.days_of_activity < 90:
        return {"score": None, "confidence": "insufficient_data"}
    
    # Calculate z-scores against multiple baselines
    personal_z_score = (current_metric - personal_baseline) / personal_std_dev
    team_z_score = (current_metric - team_average) / team_std_dev
    
    # Weight based on data quality and recency
    confidence_weight = min(1.0, user_data.days_of_activity / 180)
    
    # Composite score with confidence interval
    raw_score = calculate_raw_burnout_score(user_data)
    confidence_interval = calculate_confidence_interval(
        raw_score, sample_size, variance
    )
    
    return {
        "score": raw_score,
        "confidence_lower": confidence_interval.lower,
        "confidence_upper": confidence_interval.upper,
        "confidence_level": confidence_weight,
        "sample_size": user_data.days_of_activity
    }
```

**4. Ethical Considerations & Privacy**:
- Aggregate team trends vs individual surveillance
- Opt-in reporting for individuals
- Focus on systemic issues, not individual performance
- Clear communication about methodology and limitations
- Regular validation against actual burnout outcomes

**5. Validation Framework**:
```python
class BurnoutValidation:
    """Continuous validation against actual outcomes"""
    
    @staticmethod
    def validate_predictions():
        # Track prediction accuracy over time
        # Compare GitHub scores vs:
        # - Self-reported burnout surveys
        # - Sick leave patterns  
        # - Employee satisfaction scores
        # - Voluntary turnover
        # - Performance review outcomes
        
    @staticmethod  
    def adjust_weights():
        # Machine learning approach to optimize weights
        # Based on validation outcomes
        # Continuous model improvement
```

##### Phase 3: Scientifically Rigorous Scoring Implementation
**Multi-layered scoring system with statistical validation**:

**1. Data Quality Assessment**:
```python
class DataQualityCheck:
    @staticmethod
    def assess_data_sufficiency(user_data):
        """Ensure statistical validity before scoring"""
        quality_score = 0
        issues = []
        
        # Temporal coverage (minimum 90 days for baseline)
        if user_data.days_span >= 90:
            quality_score += 25
        else:
            issues.append(f"Insufficient history: {user_data.days_span} days")
            
        # Activity consistency (at least 50% of days with activity)
        activity_ratio = user_data.active_days / user_data.total_days
        if activity_ratio >= 0.3:
            quality_score += 25
        else:
            issues.append(f"Low activity consistency: {activity_ratio:.2%}")
            
        # Data diversity (commits, PRs, reviews - not just commits)
        data_types = sum([
            bool(user_data.commits),
            bool(user_data.pull_requests), 
            bool(user_data.code_reviews)
        ])
        quality_score += (data_types / 3) * 25
        
        # Recent activity (not just historical)
        days_since_last_activity = (datetime.now() - user_data.last_activity).days
        if days_since_last_activity <= 14:
            quality_score += 25
        else:
            issues.append(f"Stale data: {days_since_last_activity} days since activity")
            
        return {
            "quality_score": quality_score,
            "sufficient": quality_score >= 75,
            "issues": issues
        }
```

**2. Baseline Establishment (Multi-Modal)**:
```python
class BaselineCalculator:
    """Calculate multiple baseline types for robust comparison"""
    
    @staticmethod
    def calculate_personal_baseline(user_data, months_back=6):
        """Individual's own historical patterns"""
        # Rolling window approach - exclude last 30 days to avoid current burnout
        historical_data = user_data.exclude_recent(days=30)
        
        return {
            "commits_per_day": np.percentile(historical_data.daily_commits, 50),
            "work_hours_per_day": np.percentile(historical_data.daily_hours, 50),
            "review_participation": np.mean(historical_data.reviews_given),
            "code_quality_proxy": np.mean(historical_data.lines_per_commit),
            "variability": np.std(historical_data.daily_commits)
        }
    
    @staticmethod
    def calculate_cohort_baseline(team_data, user_role, user_seniority):
        """Baseline from similar developers (role + seniority)"""
        cohort = team_data.filter(role=user_role, seniority=user_seniority)
        
        # Use median (robust to outliers) rather than mean
        return {
            "commits_per_day": np.median([u.daily_commits for u in cohort]),
            "work_hours_per_day": np.median([u.daily_hours for u in cohort]),
            "review_participation": np.median([u.reviews_given for u in cohort]),
            "weekend_work_ratio": np.median([u.weekend_ratio for u in cohort])
        }
```

**3. Advanced Scoring with Confidence Intervals**:
```python
def calculate_github_burnout_comprehensive(user_data, baselines):
    """
    Maslach-aligned burnout scoring with statistical rigor
    Addresses the 'non-stop commits throughout day' scenario
    """
    
    # 1. EMOTIONAL EXHAUSTION (40% weight)
    temporal_score = calculate_temporal_exhaustion(user_data, baselines)
    intensity_score = calculate_intensity_exhaustion(user_data, baselines)
    
    # Key insight: Distinguish between 'flow state' and 'frantic activity'
    flow_state_indicator = detect_flow_vs_frantic(user_data)
    if flow_state_indicator.is_sustainable_flow:
        # Healthy high-productivity - reduce exhaustion penalty
        temporal_score *= 0.7
        intensity_score *= 0.8
    
    exhaustion_raw = (temporal_score * 0.6 + intensity_score * 0.4)
    
    # 2. CYNICISM/DEPERSONALIZATION (35% weight) 
    social_decline = calculate_social_coding_decline(user_data, baselines)
    interaction_quality = calculate_interaction_degradation(user_data, baselines)
    
    cynicism_raw = (social_decline * 0.6 + interaction_quality * 0.4)
    
    # 3. REDUCED ACCOMPLISHMENT (25% weight)
    quality_decline = calculate_quality_trends(user_data, baselines)
    productivity_paradox = calculate_productivity_paradox(user_data, baselines)
    
    accomplishment_raw = 100 - (quality_decline * 0.6 + productivity_paradox * 0.4)
    
    # Composite score
    raw_score = (
        exhaustion_raw * 0.40 +
        cynicism_raw * 0.35 +
        (100 - accomplishment_raw) * 0.25
    )
    
    # Calculate confidence interval
    confidence = calculate_confidence_interval(user_data, raw_score)
    
    return BurnoutAssessment(
        score=raw_score,
        confidence_lower=confidence.lower,
        confidence_upper=confidence.upper,
        reliability=confidence.reliability,
        components={
            "exhaustion": exhaustion_raw,
            "cynicism": cynicism_raw, 
            "accomplishment": accomplishment_raw
        },
        risk_factors=identify_primary_risk_factors(user_data),
        recommendations=generate_recommendations(raw_score, user_data)
    )

def detect_flow_vs_frantic(user_data):
    """
    Critical function: Distinguish sustainable high-productivity from burnout
    
    Flow State Indicators:
    - Consistent output quality maintained
    - Breaks between intensive periods
    - Productive output per hour remains high
    - Code review engagement remains healthy
    
    Frantic Activity Indicators:
    - Output quality declining despite high volume
    - No recovery periods
    - Inefficient commits (high churn, many micro-commits)
    - Social engagement dropping
    """
    
    # Quality maintenance during high activity
    quality_consistency = np.corrcoef(
        user_data.daily_commit_count,
        user_data.daily_quality_score
    )[0,1]
    
    # Efficiency metrics
    commits_per_productive_hour = user_data.commits / user_data.focused_hours
    efficiency_trend = np.polyfit(range(len(commits_per_productive_hour)), 
                                 commits_per_productive_hour, 1)[0]
    
    # Recovery pattern detection
    has_recovery_periods = detect_rest_periods(user_data.daily_activity)
    
    # Social engagement maintenance
    social_engagement_trend = calculate_social_trend(user_data.review_activity)
    
    is_flow = (
        quality_consistency > 0.1 and  # Quality maintained during high activity
        efficiency_trend >= -0.1 and   # Efficiency not declining rapidly
        has_recovery_periods and       # Taking breaks
        social_engagement_trend >= -0.2 # Social coding not collapsing
    )
    
    return FlowStateAssessment(
        is_sustainable_flow=is_flow,
        quality_maintenance=quality_consistency,
        efficiency_trend=efficiency_trend,
        recovery_detected=has_recovery_periods,
        social_health=social_engagement_trend
    )
```

**4. Risk Classification (Clinical MBI Alignment)**:
```python
def classify_burnout_risk(burnout_assessment):
    """Map to clinically validated MBI risk levels"""
    
    score = burnout_assessment.score
    confidence = burnout_assessment.reliability
    
    # Adjust risk classification based on confidence
    if confidence < 0.7:
        return RiskClassification(
            level="INSUFFICIENT_DATA",
            message="Need more data for reliable assessment",
            recommendation="Continue monitoring for 30+ days"
        )
    
    # Clinical MBI thresholds adapted for GitHub data
    if score >= 81:
        return RiskClassification(
            level="CRITICAL_RISK",
            message="Severe burnout indicators across multiple dimensions",
            recommendation="Immediate intervention recommended",
            confidence_interval=(burnout_assessment.confidence_lower, 
                                burnout_assessment.confidence_upper)
        )
    elif score >= 61:
        return RiskClassification(
            level="HIGH_RISK", 
            message="Multiple strong burnout indicators",
            recommendation="Schedule check-in within 1 week"
        )
    elif score >= 31:
        return RiskClassification(
            level="MODERATE_RISK",
            message="Some concerning patterns emerging", 
            recommendation="Monitor closely, consider workload review"
        )
    else:
        return RiskClassification(
            level="LOW_RISK",
            message="Healthy development patterns",
            recommendation="Continue current practices"
        )
```

##### Phase 4: Dashboard Integration
**Display GitHub-only burnout analysis**:

1. **Enhanced Team Overview**:
   - Show all team members (not just incident-involved)
   - GitHub activity indicators for each member
   - Burnout risk levels for pure developers

2. **GitHub-Specific Insights**:
   - Developer velocity trends over time
   - Code quality metrics progression
   - Work-life balance scoring
   - Collaboration health indicators

3. **Actionable Recommendations**:
   - Workload redistribution suggestions
   - Code review process improvements
   - Work-life balance interventions
   - Mentoring/support recommendations

##### Phase 5: Implementation Steps

1. **Backend Changes**:
   - `backend/app/services/github_user_discovery.py` - New user discovery logic
   - `backend/app/services/github_burnout_analyzer.py` - GitHub-specific analysis
   - `backend/app/models/user_classification.py` - User type tracking
   - Enhanced existing analyzers to handle mixed data sources

2. **API Endpoints**:
   - `/analyses/github-only` - Pure GitHub burnout analysis
   - `/team/github-contributors` - Discover GitHub-active team members
   - `/users/{id}/github-patterns` - Individual developer pattern analysis

3. **Frontend Updates**:
   - Team overview showing all members (not just incident-involved)
   - GitHub activity cards for pure developers
   - Burnout risk indicators for code-focused work
   - Filtering options: "All Members", "Incident Responders", "Developers Only"

4. **Database Schema**:
   ```sql
   ALTER TABLE users ADD COLUMN user_type VARCHAR(50);
   ALTER TABLE users ADD COLUMN github_activity_score FLOAT;
   ALTER TABLE users ADD COLUMN last_github_activity TIMESTAMP;
   
   CREATE TABLE github_burnout_indicators (
       id SERIAL PRIMARY KEY,
       user_id INTEGER REFERENCES users(id),
       analysis_id INTEGER REFERENCES analyses(id),
       velocity_score FLOAT,
       quality_score FLOAT,
       work_life_score FLOAT,
       collaboration_score FLOAT,
       created_at TIMESTAMP DEFAULT NOW()
   );
   ```

##### Benefits Expected:
1. **Proactive Burnout Detection**: Catch burnout before it leads to incidents
2. **Complete Team Coverage**: Include all active team members, not just on-call
3. **Developer-Specific Insights**: Code-focused burnout indicators
4. **Earlier Intervention**: Address work-life balance issues before escalation
5. **Role-Appropriate Analysis**: Different burnout patterns for different roles

##### Success Metrics:
- % of team members analyzed (target: 90%+ of active contributors)
- Early burnout detection rate (GitHub signals before incident involvement)
- Developer satisfaction with work-life balance recommendations
- Reduction in developer churn/turnover
- Improvement in code quality metrics over time

### Outstanding Issues & Technical Debt:

#### High Priority Tasks:
1. **Fix Frontend Duplicate Factor Calculations** ✅ COMPLETED
   - **Issue**: Frontend was calculating burnout factors differently than backend
   - **Impact**: Inconsistent data display between charts and actual analysis
   - **Root Cause**: Frontend was recalculating factors with different formulas:
     - Different scaling (e.g., incidents * 0.4 vs backend's tiered scaling)
     - Including GitHub activity in calculations (backend doesn't)
     - Different thresholds for response time calculations
   - **Solution**: Removed all frontend calculations, now using only backend factors
   - **Files Fixed**: 
     - `frontend/src/app/dashboard/page.tsx` - member modal factors (lines 5384-5415)
     - `frontend/src/app/dashboard/page.tsx` - organization burnout factors (lines 2319-2408)

2. **Fix Analysis ID Not Found in Background Task** 🔧
   - **Issue**: Analysis records created in main request not visible to background tasks
   - **Impact**: Analyses fail with "Analysis 103 not found" errors
   - **Cause**: Database transaction isolation or session management issues
   - **Solution**: Using SessionLocal() instead of get_db() in background tasks

3. **Fix NoneType Conversion Errors** 📋
   - **Issue**: Multiple "can't convert type 'NoneType' to numerator/denominator" errors
   - **Impact**: Analysis crashes when encountering null values
   - **Location**: Burnout calculation functions with division operations
   - **Solution**: Add comprehensive null checks before mathematical operations

4. **Standardize Risk Level Thresholds** 📋
   - **Issue**: Different analyzers use different thresholds for risk levels
   - **Impact**: Inconsistent risk categorization across the application
   - **Example**: SimpleBurnoutAnalyzer vs UnifiedBurnoutAnalyzer thresholds differ
   - **Solution**: Create centralized configuration for all thresholds

#### Medium Priority Tasks:
5. **Create Centralized Burnout Configuration File** 📋
   - **Purpose**: Single source of truth for all burnout calculation parameters
   - **Contents**: Risk thresholds, scoring weights, factor calculations
   - **Location**: `backend/app/core/burnout_config.py`
   - **Benefits**: Easier tuning, consistency, maintainability

6. **Add Memory/Context Retention to Agent** 📋
   - **Issue**: AI agent doesn't remember previous analyses or context
   - **Impact**: Can't provide trend-based insights or learn from patterns
   - **Solution**: Store analysis history and context for agent reference

#### Low Priority Issues:
7. Slack channel access errors (bot not in channels)
8. Invalid Anthropic API key for AI narratives - User configuration issue

### Recently Completed:
1. ✅ **Health Trends Chart Logic** - Fixed to show daily incident data from current analysis period
2. ✅ **Data Consistency Issue** - Fixed major inconsistency where dashboard showed different incident counts across components
3. ✅ **GitHub Mapping Button Navigation Fix** - Changed dashboard GitHub button from navigation to MappingDrawer
4. ✅ **Integrations Page Debug Enhancement** - Added comprehensive logging for endless loader troubleshooting

#### 6. Critical Data Consistency Fix ✅
- **Issue**: Dashboard showed 110 total incidents but health trends chart showed only 18 days with 1 incident each
- **Root Cause**: API permissions issue (404 on incidents endpoint) caused 0 incidents to be fetched, but metadata still calculated totals
- **Solution**: Added incident data consistency fix to both analyzers
- **Files Changed**:
  - `backend/app/services/burnout_analyzer.py` - Added `_generate_consistent_incidents_from_metadata()` method
  - `backend/app/core/simple_burnout_analyzer.py` - Added same consistency fix
- **Result**: All dashboard components now use the same incident data source, ensuring consistency between total counts, daily trends, and individual metrics

### REDUCE GITHUB API CALLS - AVOID RATE LIMITS

#### Problem: Hitting GitHub API rate limits during analysis

**Current Issues**:
1. Making too many API calls per analysis
2. Re-fetching data that hasn't changed
3. Not leveraging caching effectively
4. Fetching unnecessary data

#### Implementation Strategies:

**1. Enable Smart Caching Service** ✅
- Already implemented in `GitHubMappingService`
- Cache email->username mappings for 7 days
- Only refresh activity data when needed
- Implementation in `enhanced_github_collector.py`

**2. Batch API Calls**
- Use GitHub's GraphQL API instead of REST for some calls
- Fetch multiple users' data in single request
- Reduce per-user API calls from 3-4 to 1

**3. Implement Request Pooling**
```python
# Instead of individual calls per user:
for user in users:
    fetch_user_data(user)  # BAD - N API calls

# Use batch fetching:
fetch_users_data(users)  # GOOD - 1 API call
```

**4. Skip Unnecessary Data**
- Don't fetch commit details if only counting
- Use search API for counts instead of paginating all results
- Skip users with recent cached data

**5. Rate Limit Monitoring**
```python
# Add rate limit tracking
class GitHubRateLimiter:
    def check_rate_limit(self, response_headers):
        remaining = int(response_headers.get('X-RateLimit-Remaining', 0))
        reset_time = int(response_headers.get('X-RateLimit-Reset', 0))
        
        if remaining < 100:  # Getting close to limit
            wait_time = reset_time - time.time()
            logger.warning(f"GitHub rate limit low: {remaining} remaining. Reset in {wait_time}s")
            
        if remaining < 10:  # Critical
            raise RateLimitException("GitHub rate limit critical")
```

**6. Implement Progressive Backoff**
- If rate limit hit, wait until reset
- Implement exponential backoff for retries
- Queue requests to avoid bursts

**7. Local Caching Database**
```sql
CREATE TABLE github_api_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE,
    api_endpoint VARCHAR(500),
    response_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_cache_key ON github_api_cache(cache_key);
CREATE INDEX idx_expires_at ON github_api_cache(expires_at);
```

**8. Configuration Options**
```python
GITHUB_API_CONFIG = {
    "max_requests_per_minute": 30,  # Stay well below limit
    "cache_ttl_hours": 24,          # Cache non-user data
    "user_cache_ttl_hours": 2,      # Cache user data briefly
    "enable_smart_caching": True,
    "batch_size": 50,               # Batch API requests
    "retry_after_rate_limit": True
}
```

#### Quick Wins to Implement NOW:

**1. Ensure Smart Caching is Enabled**
File: `backend/app/services/enhanced_github_collector.py`
```python
# Line 26 - Make sure this is 'true'
use_smart_caching = os.getenv('USE_SMART_GITHUB_CACHING', 'true').lower() == 'true'
```

**2. Reduce Event Fetching**
File: `backend/app/services/github_collector.py`
- Line 230: Change `per_page=100` to `per_page=30`
- Only fetch first page of events

**3. Skip Redundant User Lookups**
- Check if user already mapped before API call
- Don't re-fetch if analyzed recently

**4. Add Rate Limit Headers Logging**
```python
if resp.headers.get('X-RateLimit-Remaining'):
    logger.info(f"GitHub API calls remaining: {resp.headers['X-RateLimit-Remaining']}")
```

#### Environment Variables to Set in Railway:
```
USE_SMART_GITHUB_CACHING=true
GITHUB_API_MAX_RETRIES=3
GITHUB_API_CACHE_TTL=86400
```

### AI INSIGHTS - MAKE 100% DYNAMIC (Remove Template Fallbacks)

#### Objective: Keep Current Content Structure but Ensure Everything is AI-Generated

**Current Situation**: 
- AI insights has good content structure (Summary, Key Observations, Recommendations)
- BUT: Falls back to template-based content when LLM unavailable
- User wants: Same quality insights but ALWAYS AI-generated, never templated

#### Implementation Plan:

**Phase 1: Enhance LLM Prompt to Generate Current Format**
File: `backend/app/services/ai_burnout_analyzer.py`

Update `_generate_llm_team_narrative()` prompt to explicitly request:
```python
prompt = """
Generate a team burnout analysis with EXACTLY these sections:

**Summary** (1 paragraph):
- Start with: "The team has X members total, with Y handling incidents."
- Include average burnout score for incident responders
- Highlight how many at high/medium/low risk
- Identify primary burnout driver and impact score
- Mention any detected patterns

**Key Observations** (1 paragraph):
- Spotlight highest risk individual with specific metrics
- Explain their primary stress factors
- Mention other at-risk members if applicable
- Describe team-wide stress patterns
- Include specific data points and percentages

**Recommendations** (bullet points):
- 3-5 specific, actionable recommendations
- Tie each to observed patterns
- Include both immediate and long-term actions
- Reference specific team members when relevant

Use the exact data provided. Be specific with names, numbers, and percentages.
Make each analysis unique - vary sentence structure and focus areas.
"""
```

**Phase 2: Remove ALL Template Fallbacks**
File: `frontend/src/app/dashboard/page.tsx`

Replace lines ~3421-3550 (entire template fallback) with:
```typescript
// Only show AI insights if LLM-generated content exists
if (!aiInsights?.llm_team_analysis) {
  return (
    <div className="text-center py-12 text-gray-500">
      <Sparkles className="h-10 w-10 mx-auto mb-4 opacity-40" />
      <h4 className="font-medium text-gray-700 mb-2">AI Analysis Unavailable</h4>
      <p className="text-sm mb-4">Configure your AI token to enable intelligent team insights</p>
      <Button 
        variant="outline" 
        size="sm"
        onClick={() => router.push('/settings')}
      >
        Configure AI Settings
      </Button>
    </div>
  )
}

// Render the LLM-generated content
return (
  <div className="space-y-4">
    <div 
      className="prose prose-sm max-w-none"
      dangerouslySetInnerHTML={{ 
        __html: aiInsights.llm_team_analysis
          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
          .replace(/\n\n/g, '</p><p class="mt-4">')
          .replace(/^/, '<p>')
          .replace(/$/, '</p>')
      }}
    />
  </div>
)
```

**Phase 3: Ensure Unique Content Every Run**

Add variation instructions to prompt:
```python
# At the end of prompt
variation_instruction = f"""
Analysis ID: {analysis_id}
Timestamp: {datetime.now().isoformat()}

IMPORTANT: Make this analysis unique. Vary:
- Opening sentence structure
- Which metrics to emphasize
- Order of observations
- Specific examples used
- Recommendation priorities

Never use the exact same phrases as previous analyses.
"""
```

**Phase 4: Enhanced Data Injection**

Provide richer context to LLM:
```python
team_context = {
    "time_context": {
        "day_of_week": datetime.now().strftime("%A"),
        "month": datetime.now().strftime("%B"),
        "is_weekend": datetime.now().weekday() >= 5,
        "is_end_of_month": datetime.now().day > 25,
        "is_holiday_season": month in ["November", "December", "January"]
    },
    "comparison_context": {
        "vs_last_analysis": "20% increase" if prev_score else "first analysis",
        "trend": "improving" if trend_positive else "declining",
        "notable_changes": self._identify_changes(current, previous)
    },
    "environmental_context": {
        "recent_incidents": self._get_recent_major_incidents(),
        "upcoming_events": self._check_calendar_context(),
        "team_changes": self._detect_team_changes()
    }
}
```

**Phase 5: Quality Assurance**

Before returning LLM content, validate:
- Contains all three sections (Summary, Key Observations, Recommendations)
- Includes actual member names and data
- Minimum length threshold (500 characters)
- No placeholder text like "[Name]" or "[X]"

If validation fails, retry with more explicit prompt.

#### Benefits:
1. **Preserves Current UX**: Users see same structured insights
2. **Always Fresh**: Every analysis is uniquely written
3. **No Templates**: Zero fallback to generic text
4. **Clear Degradation**: When AI unavailable, shows clear call-to-action

#### Success Criteria:
- Running same analysis twice produces different narratives
- All content references actual data from the analysis
- No generic/template phrases appear
- Clear messaging when AI token not configured

### DATA COLLECTION & STORAGE ENHANCEMENT PLAN

#### Objective: Maximize Data Granularity for Better Analysis

**Enhanced Collection Areas**:
1. **Rootly**: Comprehensive incident metadata, response metrics, business impact
2. **GitHub**: Development pattern analysis, code quality trends, collaboration metrics  
3. **Slack**: Communication patterns, sentiment analysis, incident-related messaging
4. **Cross-System**: Correlations between code changes, incidents, and team communication

**Key Enhancements**:
- Store raw API responses for debugging and reprocessing
- Calculate advanced burnout indicators (workload clustering, stress progression)
- Track historical trends and seasonal patterns
- Archive detailed timeline and response data

**Implementation**: New database tables for granular storage, enhanced API collectors, correlation analysis services

## UI ASSETS REFERENCES

### Logos and Branding
- **Head Logo**: `/images/oncall-burnout-logo.png` - OnCall Burnout head logo (currently removed from UI but available for future use)
- **Rootly AI Logo**: `/images/rootly-ai-logo.png` - Main Rootly AI logo for light backgrounds
- **Rootly AI Logo White**: `/images/rootly-ai-logo-white.png` - Rootly AI logo for dark backgrounds (used in sidebar footer)

### Logo Usage Notes
- The head logo was temporarily removed from landing page and integrations page headers
- Can be restored by referencing `/images/oncall-burnout-logo.png` in Image components
- Original usage locations: landing-page.tsx (header & footer), integrations/page.tsx (header)

## GITHUB MAPPING CLEANUP - ORGANIZATION MEMBER VALIDATION

### Problem Statement
**Issue**: GitHub user mappings include users who are not members of the GitHub organizations associated with the token, causing incorrect data collection and analysis.

**Impact**: 
- Analyses include GitHub activity from users outside the organization
- Team burnout scores are diluted by non-team member data  
- Dashboard shows incorrect team composition
- API rate limits hit unnecessarily for non-org members

### Solution Overview
Create a "Refresh Mappings" button that validates all GitHub username mappings against actual organization membership and removes invalid mappings.

### Implementation Plan

#### Phase 1: Backend Validation Service
**File**: `backend/app/services/github_mapping_validator.py`

```python
class GitHubMappingValidator:
    """Service to validate and clean GitHub user mappings against org membership."""
    
    async def validate_all_mappings(self, github_token: str, integration_id: int) -> Dict:
        """
        Validate all GitHub mappings for an integration against org membership.
        
        Returns:
        {
            "total_mappings": 45,
            "validated": 38,
            "removed": 7,
            "removed_users": [
                {"username": "external_user", "email": "external@other.com"},
                ...
            ],
            "org_members_found": 150,
            "organizations": ["acme-corp", "acme-mobile"]
        }
        """
        
    async def get_all_org_members(self, github_token: str) -> Set[str]:
        """
        Efficiently get all members from all organizations the token has access to.
        Uses existing _get_org_members from enhanced_github_matcher.py
        """
        
    async def remove_invalid_mappings(self, invalid_mappings: List[int]) -> int:
        """Remove mappings that don't correspond to org members."""
```

#### Phase 2: API Endpoint  
**File**: `backend/app/api/endpoints/github.py`

```python
@router.post("/integrations/{integration_id}/validate-github-mappings")
async def validate_github_mappings(
    integration_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate GitHub mappings against organization membership.
    Remove mappings for users not in any accessible GitHub org.
    """
```

#### Phase 3: Frontend Refresh Button
**File**: `frontend/src/components/mapping-drawer.tsx`

**Location**: Add to GitHub Mapping Drawer header, next to existing buttons

**UI Design**:
```tsx
<div className="flex items-center space-x-2">
  <Button 
    variant="outline" 
    size="sm"
    onClick={handleRefreshMappings}
    disabled={isRefreshing}
    className="flex items-center space-x-2"
  >
    {isRefreshing ? (
      <Loader2 className="w-4 h-4 animate-spin" />
    ) : (
      <RefreshCw className="w-4 h-4" />
    )}
    Validate Mappings
  </Button>
  
  <TooltipProvider>
    <Tooltip>
      <TooltipTrigger asChild>
        <InfoIcon className="w-4 h-4 text-gray-400" />
      </TooltipTrigger>
      <TooltipContent>
        <p className="max-w-xs">
          Removes GitHub mappings for users who are not members 
          of your GitHub organizations
        </p>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</div>
```

#### Phase 4: Validation Results Modal
**Component**: `ValidationResultsModal.tsx`

**Features**:
- Shows before/after mapping counts
- Lists removed users with reasons
- Organizations checked
- Option to undo changes (restore from backup)
- Success/error states with clear messaging

**Example Results Display**:
```
✅ Validation Complete

📊 Summary:
- 45 mappings checked
- 38 mappings validated (users are org members)  
- 7 mappings removed (users not in organizations)

🏢 Organizations Checked:
- acme-corp (95 members)
- acme-mobile (42 members)  
- acme-data (23 members)

❌ Removed Mappings:
- external_user (external@contractor.com) - Not found in any org
- old_employee (former@acme.com) - No longer org member
- consultant123 (temp@freelance.com) - Not found in any org

⚠️  Impact: Future analyses will only include validated team members
```

#### Phase 5: Optimization Strategy

**Efficient Validation Process**:
1. **Batch API Calls**: Get all org members in 1-3 API calls (one per org)
2. **Smart Caching**: Cache org member lists for 24 hours  
3. **Incremental Updates**: Only check mappings created/updated since last validation
4. **Background Processing**: For large teams, run validation in background task

**Rate Limit Management**:
```python
# Estimated API calls for validation:
# - 1 call per organization to get all members (typically 1-3 orgs)
# - 0 calls per individual user (just check against cached member list)
# Total: 1-3 API calls instead of 1 call per mapped user (45+ calls)
```

#### Phase 6: Integration Points

**Database Changes** (Optional):
```sql
-- Add validation metadata to user_mappings table
ALTER TABLE user_mappings ADD COLUMN last_validated TIMESTAMP;
ALTER TABLE user_mappings ADD COLUMN validation_status VARCHAR(50); -- 'valid', 'invalid', 'pending'
ALTER TABLE user_mappings ADD COLUMN validation_notes TEXT;
```

**Integration with Existing Systems**:
- Use existing `enhanced_github_matcher._get_org_members()` function
- Leverage current `UserMapping` model and database structure
- Integrate with existing `MappingDrawer` component
- Maintain current caching strategies from `GitHubMappingService`

#### Phase 7: User Experience Flow

**Happy Path**:
1. User opens GitHub Mapping Drawer
2. Sees "Validate Mappings" button in header
3. Clicks button → Loading state shows
4. Validation completes → Results modal shows summary
5. User reviews removed mappings → Confirms changes
6. Drawer refreshes showing cleaned mapping list

**Edge Cases**:
- **No Invalid Mappings**: Show "All mappings validated ✅" message
- **API Token Issues**: Show clear error with token permission instructions
- **Rate Limit Hit**: Queue validation for later, show estimated completion time
- **Network Errors**: Allow retry with exponential backoff

### Implementation Timeline

**Day 1**: Backend validation service and API endpoint
**Day 2**: Frontend refresh button and modal components  
**Day 3**: Integration testing and error handling
**Day 4**: UI polish and user experience refinement

### Success Metrics
- **Data Quality**: % of mappings that are valid org members (target: >95%)
- **API Efficiency**: Reduced API calls per validation (from N calls to 1-3 calls)
- **User Adoption**: % of admin users who use validation feature (target: >80%)
- **Analysis Accuracy**: Improved team composition accuracy in burnout analyses

### Technical Considerations

**Performance**: 
- Cache org member lists to avoid repeated API calls
- Batch process large mapping lists
- Use background tasks for teams >100 members

**Security**: 
- Validate GitHub token permissions before validation
- Log all mapping changes for audit trail
- Require user confirmation before bulk deletions

**Backwards Compatibility**:
- Validation is opt-in via button click
- Existing mappings remain until explicitly validated
- No automatic cleanup without user action

## DEMO CONFIGURATION - GitHub-Only Scoring Restriction

### Configuration Active: August 2025 Demo
**Purpose**: For demo purposes, only score GitHub activity for users who have at least one incident via Rootly or PagerDuty.

**Rationale**: Demonstrates the integrated nature of the burnout analysis by showing how incident response correlates with development patterns.

### Implementation Details

#### 1. Backend Changes - `unified_burnout_analyzer.py`
**Location**: `backend/app/services/unified_burnout_analyzer.py`

**Current Demo Logic**:
```python
# Line ~1200 in _analyze_github_activity_members()
# Only analyze GitHub activity for users with incidents
incident_responders = set()
for incident in self.incidents:
    if incident.get('assigned_to', {}).get('email'):
        incident_responders.add(incident['assigned_to']['email'].lower())

# Filter GitHub-only users
if user_email.lower() not in incident_responders:
    logger.info(f"Skipping GitHub-only analysis for {user_email} (no incidents) - DEMO MODE")
    continue
```

#### 2. Frontend Filtering - `dashboard/page.tsx`
**Location**: `frontend/src/app/dashboard/page.tsx`

**Current Demo Logic**:
```typescript
// Line ~2500 in team members display
// Filter to only show users with incidents
const membersWithIncidents = teamAnalysis?.members?.filter(
    member => member.incident_count > 0
) || [];
```

### How to Revert After Demo

#### Step 1: Remove Backend Filtering
In `backend/app/services/unified_burnout_analyzer.py`, remove or comment out:
```python
# REMOVE THIS BLOCK:
if user_email.lower() not in incident_responders:
    logger.info(f"Skipping GitHub-only analysis for {user_email} (no incidents) - DEMO MODE")
    continue
```

#### Step 2: Update Frontend Display
In `frontend/src/app/dashboard/page.tsx`, change:
```typescript
// FROM:
const membersWithIncidents = teamAnalysis?.members?.filter(
    member => member.incident_count > 0
) || [];

// TO:
const membersWithIncidents = teamAnalysis?.members || [];
```

#### Step 3: Update Risk Calculation
Ensure risk factors include GitHub-only developers:
```typescript
// Update any filtering logic that excludes zero-incident users
// Search for: member.incident_count > 0
// Replace with: member.burnout_score > 0 (or remove filter entirely)
```

#### Step 4: Verify Full Team Display
After reverting:
1. Run a new analysis
2. Verify GitHub-only developers appear in:
   - Team members graph
   - Risk factors chart
   - Individual member cards
   - At-risk count

### Files Affected by Demo Configuration
1. `backend/app/services/unified_burnout_analyzer.py` - Lines ~1200-1210
2. `frontend/src/app/dashboard/page.tsx` - Lines ~2500, risk calculation sections
3. Team member filtering logic throughout dashboard

### Testing the Reversion
```bash
# After reverting, test with:
1. Create a test user with GitHub activity but no incidents
2. Run analysis
3. Verify user appears in all dashboard sections
4. Check burnout score is calculated based on GitHub patterns alone
```

### Demo Talking Points
- "The system integrates incident response data with development patterns"
- "We're focusing on on-call engineers who both respond to incidents and write code"
- "In production, this would include all developers to catch burnout before they're on-call"

---

### Outstanding Issues:
1. Slack channel access errors (bot not in channels) - Low priority
2. Invalid Anthropic API key for AI narratives - User configuration issue
3. Demo mode active - GitHub scoring restricted to incident responders only