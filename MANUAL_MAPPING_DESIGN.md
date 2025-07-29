# Manual Mapping Panel Design Document

## Overview

Manual mappings allow users to explicitly define correlations between team members across different platforms (Rootly/PagerDuty ↔ GitHub ↔ Slack) when automatic detection fails or produces incorrect results.

## Current State Analysis

### Existing Manual Mappings in Codebase

**GitHub Collector** (`app/services/github_collector.py`):
```python
self.manual_email_mappings = {
    "spencer.cheng@rootly.com": "spencerhcheng",
    "jasmeet.singh@rootly.com": "jasmeetluthra", 
    "sylvain@rootly.com": "sylvainkalache",
    # ... more mappings
}
```

**Slack Collector** (`app/services/slack_collector.py`):
```python
self.name_to_slack_mappings = {
    "Spencer Cheng": "Spencer Cheng",  # Name-based matching
    "Jasmeet Singh": "Jasmeet Singh",
    # ... more mappings
}

self.email_to_slack_mappings = {
    "spencer.cheng@rootly.com": "U093A3G69GC",
    "jasmeet.singh@rootly.com": "U002JASMEET",
    # ... more mappings
}
```

## Problem Statement

Currently, manual mappings are:
- ✅ **Hardcoded in Python files** - requires code changes and deployments
- ✅ **Not visible to end users** - no way to see what mappings exist
- ✅ **Not user-manageable** - only developers can add/modify mappings
- ✅ **Not persistent** - stored in code, not database
- ✅ **Not auditable** - no history of changes or who made them

## Solution: Manual Mapping Management Panel

### 1. Database Storage

**New Model: `UserMapping`**
```python
class UserMapping(Base):
    __tablename__ = "user_mappings"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Source platform identification
    source_platform = Column(String(50), nullable=False)  # "rootly", "pagerduty"
    source_identifier = Column(String(255), nullable=False)  # email, name
    
    # Target platform mapping
    target_platform = Column(String(50), nullable=False)  # "github", "slack"
    target_identifier = Column(String(255), nullable=False)  # username, user_id
    
    # Mapping metadata
    mapping_type = Column(String(50), default="manual")  # "manual", "auto_detected", "verified"
    confidence_score = Column(Float, nullable=True)  # For auto-detected mappings
    last_verified = Column(DateTime, nullable=True)
    
    # Audit trail
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])
```

### 2. UI Design Concepts

#### Option A: Dedicated Mapping Management Page

**Location**: `/integrations/mappings`

**Features**:
- 📊 **Overview Dashboard**: Success rates, total mappings, recent activity
- 🔍 **Search & Filter**: By platform, status, team member
- ➕ **Add New Mapping**: Guided wizard interface
- ✏️ **Edit Existing**: Inline editing with validation
- 📈 **Mapping Analytics**: Which mappings are working/failing
- 🔄 **Bulk Operations**: Import/export, bulk validation

#### Option B: Integrated into Integrations Page

**Location**: Add "Manage Mappings" buttons next to GitHub/Slack integration status

**Features**:
- 🎯 **Platform-Specific View**: Show only GitHub or Slack mappings
- 📱 **Modal Interface**: Quick add/edit without page navigation
- 📊 **Inline Status**: Show mapping status directly in integration cards

#### Option C: Team Management Integration

**Location**: New "Team" section with member-centric view

**Features**:
- 👥 **Member-Centric View**: See all platform mappings per team member
- 🔗 **Cross-Platform Linking**: Visual connection between platforms
- ✅ **Verification Status**: Manual verification of auto-detected mappings

### 3. Recommended UI Flow

#### 3.1 Main Mapping Management Panel

**Navigation**: Integrations page → "Manage Data Mappings" button → Full mapping panel

```
┌─ Manual Data Mappings ─────────────────────────────────────────┐
│                                                                │
│ 📊 Overview                                                    │
│ ├─ Total Mappings: 24                                         │
│ ├─ Success Rate: 87%                                          │
│ └─ Last Updated: 2 hours ago                                  │
│                                                                │
│ 🔍 [Search team members...] [Filter: All Platforms ▼]        │
│                                                                │
│ 📋 Mappings Table                                             │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │ Team Member       │ GitHub          │ Slack            │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ Spencer Cheng     │ ✅ spencerhcheng │ ✅ @spencer      │ │
│ │ spencer@rootly... │                 │   U093A3G69GC    │ │
│ │ [Edit] [Test]     │                 │                  │ │
│ ├──────────────────────────────────────────────────────────┤ │
│ │ John Doe          │ ❌ Not mapped    │ ⚠️ Auto-detected │ │
│ │ john@rootly.com   │                 │   @john.doe      │ │
│ │ [Map] [Test]      │                 │   [Verify]       │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                                │
│ [+ Add New Mapping] [Import CSV] [Export] [Bulk Test]         │
└────────────────────────────────────────────────────────────────┘
```

#### 3.2 Add/Edit Mapping Modal

```
┌─ Add Manual Mapping ───────────────────────────────────┐
│                                                        │
│ 👤 Team Member                                         │
│ Email: [spencer.cheng@rootly.com        ] [🔍 Search]  │
│ Name:  [Spencer Cheng                   ]              │
│                                                        │
│ 🎯 Target Platform                                     │
│ Platform: [GitHub ▼]                                   │
│                                                        │
│ 🔗 GitHub Account                                      │
│ Username: [spencerhcheng                ] [🔍 Verify]  │
│ [ ] Auto-detect from commits                           │
│                                                        │
│ ✅ Validation                                          │
│ Status: ✅ Username exists and has recent activity      │
│                                                        │
│ [Cancel] [Save Mapping]                                │
└────────────────────────────────────────────────────────┘
```

#### 3.3 Quick Actions in Integration Cards

```
┌─ GitHub Connected ─────────────────────────────────────┐
│ ✅ spencerhcheng                                       │
│ [🔧 Test] [📊 View Mappings] [⚙️ Settings] [🗑️ Remove] │
└────────────────────────────────────────────────────────┘

📊 View Mappings Modal:
┌─ GitHub Data Mappings ─────────────────────────────────┐
│ 📈 Success Rate: 8/10 (80%)                           │
│                                                        │
│ ✅ Mapped (8):                                         │
│ • spencer@rootly.com → spencerhcheng                   │
│ • jasmeet@rootly.com → jasmeetluthra                   │
│ • sylvain@rootly.com → sylvainkalache                  │
│                                                        │
│ ❌ Failed (2):                                         │
│ • john@rootly.com → No GitHub activity                 │
│ • jane@rootly.com → User not found                     │
│                                                        │
│ [+ Add Mapping] [Manage All Mappings]                 │
└────────────────────────────────────────────────────────┘
```

### 4. Implementation Plan

#### Phase 1: Database & API (1-2 days)
- [ ] Create `UserMapping` model
- [ ] Add database migration
- [ ] Create CRUD API endpoints (`/api/mappings/manual`)
- [ ] Add validation and testing endpoints

#### Phase 2: Basic UI (2-3 days)
- [ ] Add "Manage Mappings" buttons to integration cards
- [ ] Create mapping table component
- [ ] Implement add/edit mapping modal
- [ ] Add basic search and filtering

#### Phase 3: Advanced Features (2-3 days)
- [ ] Bulk operations (import/export CSV)
- [ ] Auto-detection suggestions
- [ ] Mapping validation and testing
- [ ] Analytics and success rate tracking

#### Phase 4: Integration (1 day)
- [ ] Update collectors to use database mappings
- [ ] Add fallback to hardcoded mappings
- [ ] Deploy and test in production

### 5. API Endpoints Design

```typescript
// Get all mappings for current user
GET /api/mappings/manual
Response: {
  mappings: UserMapping[],
  statistics: {
    total: number,
    by_platform: Record<string, number>,
    success_rate: number
  }
}

// Create new mapping
POST /api/mappings/manual
Body: {
  source_platform: "rootly",
  source_identifier: "spencer@rootly.com", 
  target_platform: "github",
  target_identifier: "spencerhcheng"
}

// Validate mapping
POST /api/mappings/manual/validate
Body: {
  target_platform: "github",
  target_identifier: "spencerhcheng"
}
Response: {
  valid: boolean,
  exists: boolean,
  activity_score: number,
  last_activity: string,
  suggestions?: string[]
}

// Bulk operations
POST /api/mappings/manual/bulk
Body: {
  operation: "import" | "export" | "test",
  data?: UserMapping[]
}

// Auto-detection suggestions
GET /api/mappings/suggestions?platform=github&email=spencer@rootly.com
Response: {
  suggestions: Array<{
    target_identifier: string,
    confidence: number,
    evidence: string[]
  }>
}
```

### 6. User Experience Flows

#### 6.1 First-Time Setup
1. User connects GitHub/Slack integration
2. System shows mapping status (e.g., "5/10 team members mapped")
3. User clicks "Improve Mappings" to open management panel
4. Guided setup helps map unmapped team members

#### 6.2 Ongoing Management
1. User runs analysis and sees some missing data
2. Clicks mapping data button in integration card
3. Sees which mappings failed and why
4. Quickly adds manual mappings for failed ones

#### 6.3 Team Onboarding
1. New team member joins and appears in incident data
2. System detects unmapped user in next analysis
3. Admin gets notification to add mapping
4. Quick-add flow suggests potential matches

### 7. Advanced Features

#### 7.1 Smart Suggestions
- **Email Analysis**: Match similar email patterns
- **Name Matching**: Fuzzy matching for names
- **Activity Correlation**: Match based on incident timing
- **Domain Patterns**: Learn from existing mappings

#### 7.2 Verification System
- **Manual Verification**: Users can mark auto-detected mappings as verified
- **Activity Validation**: Check if mapped accounts have relevant activity
- **Periodic Re-verification**: Automatically test mappings periodically

#### 7.3 Analytics & Insights
- **Mapping Health Dashboard**: Overall mapping success rates
- **Platform-Specific Metrics**: GitHub vs Slack mapping effectiveness
- **Team Coverage**: Which team members need attention
- **Historical Trends**: Mapping success over time

### 8. Migration Strategy

#### 8.1 Gradual Migration
1. **Keep existing hardcoded mappings** as fallback
2. **Add database mappings** as primary source
3. **Migrate hardcoded mappings** to database over time
4. **Remove hardcoded mappings** once database is complete

#### 8.2 Backward Compatibility
```python
# Enhanced mapping lookup with fallback
def get_mapping(self, email: str, platform: str) -> str:
    # 1. Check database mappings first
    db_mapping = self.get_database_mapping(email, platform)
    if db_mapping:
        return db_mapping
    
    # 2. Fallback to hardcoded mappings
    if platform == "github":
        return self.manual_email_mappings.get(email)
    elif platform == "slack":
        return self.email_to_slack_mappings.get(email)
    
    return None
```

## Success Metrics

- **Mapping Coverage**: Increase from 70% to 95%+ team member mapping
- **Data Quality**: Reduce "no data found" errors by 80%
- **User Satisfaction**: Self-service mapping management
- **Maintenance**: Reduce developer time spent on mapping issues
- **Adoption**: 90%+ of teams use manual mapping features

## Future Enhancements

- **SSO Integration**: Auto-map using corporate directory
- **AI-Powered Suggestions**: Machine learning for better auto-detection
- **Webhook Integration**: Real-time mapping validation
- **Team Sync**: Integration with HR systems for team changes
- **Mobile App**: Quick mapping management on mobile devices

---

*This design document provides a comprehensive roadmap for implementing user-manageable manual mappings, transforming a developer-only feature into a powerful self-service tool for end users.*