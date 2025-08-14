# Individual Daily Health Timeline Implementation Plan

## Overview

Enable individual daily health tracking that shows each user's health score progression over the analysis period, calculated using the existing burnout scoring algorithm. Days without incident involvement show as grey bars to indicate no data.

## Current State

- ✅ Backend stores `individual_daily_data` in analysis results
- ✅ API endpoint `/analyses/{id}/members/{email}/daily-health` exists
- ❌ Frontend shows loading spinner or "no data" message for most users
- ❌ No visual representation for "no data" days
- ❌ Inconsistent with existing scoring algorithm

## Implementation Strategy

### Phase 1: Backend Data Enhancement

#### 1.1 Ensure Complete Individual Daily Tracking
**File**: `backend/app/services/unified_burnout_analyzer.py`

**Current Issue**: Individual daily data only stored for users with incidents on specific days

**Enhancement**:
```python
def _generate_daily_trends_with_individual_tracking(self, users, incidents, days_analyzed):
    # For EVERY user in the team, create daily entries for ALL days in analysis period
    individual_daily_data = {}
    
    for user in users:
        user_email = user.get('email', '').lower()
        if not user_email:
            continue
            
        # Initialize daily data for ALL days in analysis period
        individual_daily_data[user_email] = {}
        
        for day_offset in range(days_analyzed):
            date_obj = datetime.now() - timedelta(days=days_analyzed - day_offset - 1)
            date_str = date_obj.strftime('%Y-%m-%d')
            
            # Initialize with default "no incident" state
            individual_daily_data[user_email][date_str] = {
                "incident_count": 0,
                "severity_weighted_count": 0,
                "after_hours_count": 0,
                "weekend_count": 0,
                "response_times": [],
                "has_data": False  # Flag to indicate if real incident data exists
            }
    
    # Then populate with actual incident data where it exists
    for incident in incidents:
        # ... existing incident processing logic
        # Set has_data = True when real incident involvement found
```

#### 1.2 Daily Health Score Calculation
**File**: `backend/app/services/unified_burnout_analyzer.py`

**Create consistent scoring method**:
```python
def calculate_daily_health_score(self, user_email: str, date: str, day_data: Dict) -> Dict:
    """
    Calculate individual daily health score using the same algorithm as overall burnout scoring.
    Returns health score (0-100) and metadata.
    """
    if not day_data.get('has_data', False):
        return {
            "health_score": None,  # No score for days without data
            "has_data": False,
            "factors": None
        }
    
    # Use existing burnout calculation methodology
    incident_count = day_data.get('incident_count', 0)
    severity_weighted = day_data.get('severity_weighted_count', 0)
    after_hours = day_data.get('after_hours_count', 0)
    
    # Apply same scoring logic as overall burnout analysis
    workload_factor = self._calculate_workload_factor(incident_count, severity_weighted)
    stress_factor = self._calculate_stress_factor(after_hours, weekend_count)
    response_factor = self._calculate_response_factor(day_data.get('response_times', []))
    
    # Convert to health score (inverse of burnout)
    burnout_score = self._calculate_composite_burnout_score(
        workload_factor, stress_factor, response_factor
    )
    health_score = max(5, min(100, 105 - (burnout_score * 10)))
    
    return {
        "health_score": round(health_score),
        "has_data": True,
        "factors": {
            "workload": workload_factor,
            "stress": stress_factor, 
            "response_time": response_factor
        },
        "incident_count": incident_count,
        "metadata": {
            "severity_weighted": severity_weighted,
            "after_hours": after_hours
        }
    }
```

#### 1.3 Enhanced API Endpoint
**File**: `backend/app/api/endpoints/analyses.py`

**Update existing endpoint**:
```python
@router.get("/{analysis_id}/members/{member_email}/daily-health")
async def get_member_daily_health(analysis_id: int, member_email: str, ...):
    """Enhanced individual daily health with no-data handling."""
    
    # ... existing validation logic
    
    daily_health_scores = []
    user_daily_data = individual_daily_data.get(member_email.lower(), {})
    
    # Process ALL days in analysis period, not just incident days
    for date_str in sorted(user_daily_data.keys()):
        day_data = user_daily_data[date_str]
        
        # Calculate health score (may return None for no-data days)
        health_result = analyzer._calculate_daily_health_score(
            member_email, date_str, day_data
        )
        
        daily_health_scores.append({
            "date": date_str,
            "health_score": health_result["health_score"],
            "has_data": health_result["has_data"],
            "incident_count": health_result.get("incident_count", 0),
            "factors": health_result.get("factors"),
            "team_health": team_health_by_date.get(date_str, 50)
        })
    
    return {
        "status": "success",
        "data": {
            "daily_health": daily_health_scores,
            "summary": {
                "total_days": len(daily_health_scores),
                "days_with_data": len([d for d in daily_health_scores if d["has_data"]]),
                "days_without_data": len([d for d in daily_health_scores if not d["has_data"]]),
                "avg_health_score": calculate_average_excluding_null(daily_health_scores)
            }
        }
    }
```

### Phase 2: Frontend Chart Enhancement

#### 2.1 Chart Component Update
**File**: `frontend/src/app/dashboard/page.tsx`

**Enhanced IndividualDailyHealthChart**:
```typescript
function IndividualDailyHealthChart({ memberData, analysisId, currentAnalysis }) {
  // ... existing state and fetch logic
  
  const renderCustomBar = (props: any) => {
    const { payload, x, y, width, height } = props;
    
    if (!payload.has_data) {
      // Grey bar for no-data days
      return (
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill="#E5E7EB"
          stroke="#9CA3AF"
          strokeWidth={1}
          strokeDasharray="2,2"
        />
      );
    }
    
    // Color-coded bar based on health score
    const healthScore = payload.health_score;
    let fillColor = '#EF4444'; // Red for poor health
    if (healthScore >= 70) fillColor = '#10B981'; // Green for good health
    else if (healthScore >= 50) fillColor = '#F59E0B'; // Yellow for moderate
    
    return (
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        fill={fillColor}
        stroke={fillColor}
      />
    );
  };

  return (
    <div>
      <h3 className="text-lg font-semibold mb-4">📈 Individual Daily Health Timeline</h3>
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <div className="mb-4 flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Daily health scores over {dailyHealthData.length} days
          </p>
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-green-500 rounded"></div>
              <span>Good (70+)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-yellow-500 rounded"></div>
              <span>Moderate (50-69)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-red-500 rounded"></div>
              <span>Poor (&lt;50)</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-3 h-3 bg-gray-300 rounded border-dashed border"></div>
              <span>No Data</span>
            </div>
          </div>
        </div>
        
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={dailyHealthData}>
            <CartesianGrid strokeDasharray="3,3" />
            <XAxis 
              dataKey="day_name" 
              tick={{ fontSize: 12 }}
              angle={-45}
              textAnchor="end"
              height={60}
            />
            <YAxis 
              domain={[0, 100]}
              tick={{ fontSize: 12 }}
              label={{ value: 'Health Score', angle: -90, position: 'insideLeft' }}
            />
            <Tooltip 
              content={({ active, payload, label }) => {
                if (active && payload && payload[0]) {
                  const data = payload[0].payload;
                  return (
                    <div className="bg-white p-3 border rounded-lg shadow-lg">
                      <p className="font-semibold">{label}</p>
                      {data.has_data ? (
                        <>
                          <p className="text-sm">Health Score: {data.health_score}/100</p>
                          <p className="text-sm">Incidents: {data.incident_count}</p>
                          <p className="text-sm">Team Health: {data.team_health}/100</p>
                        </>
                      ) : (
                        <p className="text-sm text-gray-500">No incident involvement this day</p>
                      )}
                    </div>
                  );
                }
                return null;
              }}
            />
            <Bar 
              dataKey="health_score"
              shape={renderCustomBar}
            />
          </BarChart>
        </ResponsiveContainer>
        
        <div className="mt-4 text-xs text-gray-600">
          <p>
            Health scores are calculated only for days with incident involvement. 
            Grey bars indicate days without incident data for this team member.
          </p>
        </div>
      </div>
    </div>
  );
}
```

### Phase 3: Data Migration & Testing

#### 3.1 Migration for Existing Analyses
**File**: `backend/migration_scripts/add_individual_daily_complete.py`

```python
async def migrate_existing_analyses():
    """
    Migrate existing analyses to have complete individual daily tracking.
    Re-process analyses to fill in missing daily entries for all users.
    """
    
    db = SessionLocal()
    try:
        # Get analyses that need migration (missing complete individual_daily_data)
        analyses_to_migrate = db.query(Analysis).filter(
            Analysis.status == 'completed',
            Analysis.results.isnot(None)
        ).all()
        
        for analysis in analyses_to_migrate:
            if not analysis.results.get('individual_daily_data'):
                logger.info(f"Migrating analysis {analysis.id} - no individual daily data")
                continue
                
            # Check if individual_daily_data is incomplete (missing days)
            individual_data = analysis.results['individual_daily_data']
            days_analyzed = analysis.results.get('period_summary', {}).get('days_analyzed', 30)
            
            needs_migration = False
            for user_email, user_data in individual_data.items():
                if len(user_data) < days_analyzed:
                    needs_migration = True
                    break
            
            if needs_migration:
                logger.info(f"Migrating analysis {analysis.id} - incomplete daily data")
                # Re-run individual daily tracking for this analysis
                # ... migration logic
                
    finally:
        db.close()
```

#### 3.2 Testing Strategy

**Unit Tests**:
- Test health score calculation consistency with overall burnout algorithm
- Test no-data day handling
- Test API endpoint with mixed data/no-data scenarios

**Integration Tests**:
- Test complete analysis flow with individual daily tracking
- Test frontend chart rendering with mixed data
- Test tooltip behavior for no-data days

**Manual Testing Checklist**:
- [ ] User with incidents shows health progression
- [ ] User with no incidents shows appropriate grey bars
- [ ] User with mixed incident/no-incident days shows both
- [ ] Tooltip correctly identifies no-data vs. data days
- [ ] Health scores align with overall burnout methodology
- [ ] Chart legend correctly explains all bar types

### Phase 4: Performance & UX Optimization

#### 4.1 Performance Considerations

**Backend Optimization**:
- Cache individual daily calculations during analysis
- Optimize API endpoint query performance
- Consider pagination for very long analysis periods

**Frontend Optimization**:
- Lazy load chart component
- Optimize re-renders on data updates
- Consider virtualization for long timelines

#### 4.2 User Experience Enhancements

**Chart Interactions**:
- Hover states for better data exploration
- Click to see detailed day breakdown
- Zoom functionality for long timelines

**Progressive Disclosure**:
- Summary stats above chart
- Expandable detailed view
- Export functionality

## Success Metrics

### Technical Metrics
- ✅ 100% of users have daily entries for all analysis days
- ✅ Health score calculation consistency with overall burnout algorithm
- ✅ API response time < 500ms for daily health data
- ✅ Zero frontend loading errors

### User Experience Metrics
- ✅ Clear visual distinction between data/no-data days
- ✅ Intuitive tooltip information
- ✅ Consistent color coding with rest of application
- ✅ Responsive chart performance

### Data Quality Metrics
- ✅ No missing days in individual timelines
- ✅ Health scores correlate appropriately with incident involvement
- ✅ No fabricated data mixing with real data

## Rollout Plan

### Phase 1 (Week 1): Backend Foundation
- Implement complete individual daily tracking
- Update health score calculation methodology
- Enhance API endpoint

### Phase 2 (Week 2): Frontend Implementation
- Build enhanced chart component
- Implement no-data day visualization
- Add comprehensive tooltips and legends

### Phase 3 (Week 3): Testing & Migration
- Run migration script for existing analyses
- Comprehensive testing across data scenarios
- Performance optimization

### Phase 4 (Week 4): Deployment & Monitoring
- Deploy to production
- Monitor performance and user feedback
- Iterative improvements based on usage

## Risk Mitigation

### Data Integrity Risks
- **Risk**: Inconsistent health calculations
- **Mitigation**: Use same scoring algorithm, comprehensive testing

### Performance Risks  
- **Risk**: Slow API responses for long timelines
- **Mitigation**: Pagination, caching, query optimization

### User Experience Risks
- **Risk**: Confusion about no-data days
- **Mitigation**: Clear visual design, explanatory tooltips, legend

### Migration Risks
- **Risk**: Data loss during analysis migration
- **Mitigation**: Backup existing data, gradual rollout, rollback plan