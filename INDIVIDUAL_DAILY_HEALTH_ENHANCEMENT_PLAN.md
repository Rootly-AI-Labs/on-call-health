# Individual Daily Health Enhancement Plan
## (Updated to work with existing implementation)

## Current State Analysis

### ✅ What Already Exists
- **API Endpoint**: `GET /analyses/{id}/members/{email}/daily-health` (fully implemented)
- **Backend Calculation**: `calculate_individual_daily_health()` method (fully implemented)
- **Data Storage**: `individual_daily_data` in analysis results (working)
- **Frontend Component**: `IndividualDailyHealthChart` (basic implementation)

### ❌ What's Missing
- **Complete day coverage**: Only stores/shows days with incidents
- **Grey bar visualization**: No handling for no-data days
- **Consistent UI**: Chart doesn't match the grey bar requirement

## Enhancement Strategy (Minimal Changes)

### Phase 1: Backend Data Enhancement

#### 1.1 Modify UnifiedBurnoutAnalyzer to Store ALL Days
**File**: `backend/app/services/unified_burnout_analyzer.py`
**Location**: Line 1741 - `_generate_daily_trends_with_individual_tracking()`

**CHANGE**: Initialize daily entries for ALL users and ALL days:

```python
# BEFORE (line 1741):
individual_daily_data = {}  # New: track per-user daily data

# AFTER:
individual_daily_data = {}  # Track per-user daily data for ALL days

# NEW: Initialize ALL users with ALL days (even zero-incident days)
all_users = set()
for user in users:
    if user.get('email'):
        all_users.add(user['email'].lower())

# Initialize every user with every day in the analysis period
for user_email in all_users:
    individual_daily_data[user_email] = {}
    for day_offset in range(days_analyzed):
        date_obj = datetime.now() - timedelta(days=days_analyzed - day_offset - 1)  
        date_str = date_obj.strftime('%Y-%m-%d')
        individual_daily_data[user_email][date_str] = {
            "date": date_str,
            "incident_count": 0,
            "severity_weighted_count": 0.0,
            "after_hours_count": 0,
            "weekend_count": 0,
            "response_times": [],
            "has_data": False  # Key flag for grey bars
        }

# Then populate with actual incident data (existing logic)
# Set has_data = True when real incidents exist
```

#### 1.2 Modify API Endpoint to Return ALL Days
**File**: `backend/app/api/endpoints/analyses.py`
**Location**: Line 1779 - `get_member_daily_health()`

**CHANGE**: Remove the incident-only filter:

```python
# BEFORE (line 1779-1780):
if incident_count == 0:
    continue  # Only show days with incidents

# AFTER: 
# Remove this filter entirely - show ALL days
```

**ADD**: Include `has_data` flag in response:

```python
# MODIFY (line 1823-1828):
daily_health_scores.append({
    "date": date_str,
    "health_score": round(daily_health_score * 10) if day_data.get("has_data", False) else None,
    "has_data": day_data.get("has_data", False),  # NEW: Flag for frontend
    "incident_count": incident_count,
    "team_health": round(team_health_by_date.get(date_str, 0) * 10),
    "factors": factors if day_data.get("has_data", False) else None,  # Only show factors if data exists
})
```

### Phase 2: Frontend Enhancement (Minimal Changes)

#### 2.1 Update Existing Chart Component
**File**: `frontend/src/app/dashboard/page.tsx`
**Location**: Line 392 - `IndividualDailyHealthChart`

**CHANGE**: Add grey bar rendering logic:

```typescript
// ADD to existing chart:
const CustomBar = (props: any) => {
  const { payload, ...rest } = props;
  
  if (!payload.has_data) {
    // Grey dashed bar for no-data days
    return (
      <rect
        {...rest}
        fill="none"
        stroke="#9CA3AF" 
        strokeWidth={1}
        strokeDasharray="3,3"
        className="opacity-60"
      />
    );
  }
  
  // Existing color logic for data days
  const score = payload.health_score;
  const color = score >= 70 ? '#10B981' : score >= 50 ? '#F59E0B' : '#EF4444';
  return <rect {...rest} fill={color} />;
};

// UPDATE existing BarChart:
<Bar 
  dataKey="health_score" 
  shape={CustomBar}  // Use custom renderer
/>
```

**ADD**: Update legend to include grey bars:

```typescript
// ADD to existing legend:
<div className="flex items-center space-x-1">
  <div className="w-3 h-3 border border-gray-400 border-dashed bg-transparent rounded"></div>
  <span>No Incident Data</span>
</div>
```

#### 2.2 Update Tooltip Logic
**CHANGE**: Handle no-data days in tooltip:

```typescript
// UPDATE existing tooltip:
<Tooltip 
  content={({ active, payload, label }) => {
    if (active && payload?.[0]) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <p className="font-semibold">{label}</p>
          {data.has_data ? (
            <>
              <p>Health Score: {data.health_score}/100</p>
              <p>Incidents: {data.incident_count}</p>
            </>
          ) : (
            <p className="text-gray-500 italic">No incident involvement</p>
          )}
        </div>
      );
    }
    return null;
  }}
/>
```

### Phase 3: Data Migration

#### 3.1 Update Existing Analyses
**NEW FILE**: `backend/migration_individual_daily_complete.py`

```python
async def fill_missing_daily_entries():
    """Add missing no-incident days to existing analyses."""
    
    analyses = db.query(Analysis).filter(Analysis.status == 'completed').all()
    
    for analysis in analyses:
        if not analysis.results.get('individual_daily_data'):
            continue
            
        individual_data = analysis.results['individual_daily_data']  
        days_analyzed = analysis.results.get('period_summary', {}).get('days_analyzed', 30)
        
        # Check if any user is missing days
        needs_update = False
        for user_email, user_data in individual_data.items():
            if len(user_data) < days_analyzed:
                needs_update = True
                break
                
        if needs_update:
            # Fill in missing days with no-data entries
            for user_email, user_data in individual_data.items():
                # ... fill missing dates with has_data: False entries
            
            # Save updated analysis
            analysis.results['individual_daily_data'] = individual_data
            db.commit()
```

## Risk Mitigation

### 1. **Backward Compatibility**
- ✅ API response structure stays the same (just adds `has_data` field)
- ✅ Frontend changes are additive (existing chart still works)
- ✅ Database structure unchanged (just more complete data)

### 2. **Performance Impact**
- ⚠️ **Risk**: Larger `individual_daily_data` objects (30 days × all users vs. only incident days)
- **Mitigation**: Monitor API response times, add pagination if needed

### 3. **Data Accuracy**
- ✅ No risk - we're adding explicit "no data" instead of hiding missing days
- ✅ Maintains existing health calculation accuracy

### 4. **Migration Complexity**  
- ✅ Low risk - just filling in missing entries with default values
- ✅ Can run incrementally without breaking existing functionality

## Implementation Timeline

### Week 1: Backend Changes
- **Day 1-2**: Modify `UnifiedBurnoutAnalyzer` to store all days
- **Day 3-4**: Update API endpoint to return all days
- **Day 5**: Test new analyses contain complete daily data

### Week 2: Frontend Changes
- **Day 1-2**: Update chart component with grey bars
- **Day 3-4**: Update tooltips and legends
- **Day 5**: Test with new and old analyses

### Week 3: Migration & Testing
- **Day 1-2**: Run migration script on existing analyses
- **Day 3-5**: Comprehensive testing across all analysis types

## Testing Strategy

### 1. **Data Validation Tests**
- ✅ Every user has entry for every day in analysis period
- ✅ Days with incidents have `has_data: true` and health scores
- ✅ Days without incidents have `has_data: false` and `health_score: null`

### 2. **UI/UX Tests** 
- ✅ Grey bars render for no-data days
- ✅ Colored bars render for data days
- ✅ Tooltips show appropriate messages
- ✅ Legend explains all bar types

### 3. **Performance Tests**
- ✅ API response time < 1s for 30-day analysis
- ✅ Frontend chart renders smoothly with mixed data
- ✅ Memory usage acceptable for large teams

## Success Metrics

### Technical
- ✅ 100% day coverage (all users × all days in analysis period)
- ✅ Clear visual distinction between data/no-data days
- ✅ API response time < 1 second

### User Experience  
- ✅ Users understand grey bars mean "no incident data"
- ✅ Timeline shows realistic progression over analysis period
- ✅ No confusion about missing vs. hidden data

This enhanced plan works WITH the existing implementation rather than replacing it, minimizing risk and development time while achieving the grey bar visualization requirement.