# Burnout Factor Calculation Discrepancies

## 1. Workload Factor

### Backend Calculation (unified_burnout_analyzer.py lines 958-968):
```python
# Scale: 0-2 incidents/week = 0-3, 2-5 = 3-7, 5-8 = 7-10, 8+ = 10
if incidents_per_week <= 2:
    workload = incidents_per_week * 1.5
elif incidents_per_week <= 5:
    workload = 3 + ((incidents_per_week - 2) / 3) * 4
elif incidents_per_week <= 8:
    workload = 7 + ((incidents_per_week - 5) / 3) * 3
else:
    workload = 10
```

### Frontend Calculation (dashboard/page.tsx lines 2331-2350):
```typescript
let workloadScore = 0;

// Incident workload component
if (m?.incident_count > 0) {
    const incidentsPerWeek = (m.incident_count || 0) / 4.3;
    workloadScore += Math.min(incidentsPerWeek * 0.4, 5);  // Different scaling!
}

// GitHub workload component (NOT IN BACKEND!)
if (m?.github_activity) {
    const commitsPerWeek = m.github_activity.commits_per_week || 0;
    if (commitsPerWeek >= 80) workloadScore += 5;
    else if (commitsPerWeek >= 50) workloadScore += 4;
    else if (commitsPerWeek >= 25) workloadScore += 2.5;
    else if (commitsPerWeek >= 15) workloadScore += 1.5;
}

return Math.min(workloadScore, 10);
```

**Issues:**
- Frontend uses different scaling (incidents * 0.4, capped at 5)
- Frontend adds GitHub activity (backend doesn't)
- Frontend divides by 4.3 weeks, backend uses direct incidents_per_week

## 2. After Hours Factor

### Backend Calculation (line 970):
```python
after_hours = min(10, (metrics.get("after_hours_percentage", 0) or 0) * 20)
```

### Frontend Calculation (lines 5418-5437):
```typescript
// Complex calculation with GitHub data
let afterHoursScore = 0;

// Incident-based after hours
if (afterHoursPercent > 0) {
    afterHoursScore = Math.min(afterHoursPercent * 20, 10);
}

// GitHub after hours activity
if (hasGitHubData && m.github_activity.after_hours_percentage > 0) {
    const githubAfterHours = m.github_activity.after_hours_percentage || 0;
    afterHoursScore = Math.max(afterHoursScore, Math.min(githubAfterHours * 15, 10));
}

return Math.min(afterHoursScore, 10);
```

**Issues:**
- Frontend considers GitHub after-hours activity
- Frontend uses Math.max to take the higher of incident vs GitHub after-hours
- Different scaling for GitHub (x15) vs incidents (x20)

## 3. Weekend Work Factor

### Backend Calculation (line 973):
```python
weekend_work = min(10, (metrics.get("weekend_percentage", 0) or 0) * 25)
```

### Frontend Calculation (lines 5440-5459):
```typescript
// Similar pattern to after hours
let weekendScore = 0;

// Incident-based weekend work
if (weekendPercent > 0) {
    weekendScore = Math.min(weekendPercent * 25, 10);
}

// GitHub weekend activity  
if (hasGitHubData && m.github_activity.weekend_percentage > 0) {
    const githubWeekend = m.github_activity.weekend_percentage || 0;
    weekendScore = Math.max(weekendScore, Math.min(githubWeekend * 20, 10));
}

return Math.min(weekendScore, 10);
```

**Issues:**
- Frontend considers GitHub weekend activity
- Different scaling for GitHub (x20) vs incidents (x25)

## 4. Incident Load Factor

### Backend Calculation (lines 976-984):
```python
# Scale: 0-3 incidents/week = 0-3, 3-6 = 3-7, 6-10 = 7-10, 10+ = 10
if incidents_per_week <= 3:
    incident_load = incidents_per_week
elif incidents_per_week <= 6:
    incident_load = 3 + ((incidents_per_week - 3) / 3) * 4
elif incidents_per_week <= 10:
    incident_load = 7 + ((incidents_per_week - 6) / 4) * 3
else:
    incident_load = 10
```

### Frontend Calculation (lines 5462-5468):
```typescript
const incidentsPerWeek = (m.incident_count || 0) / 4.3;
// Uses m?.key_metrics?.severity_weighted_per_week * 1.5, capped at 10
// Or falls back to workloadScore * 0.4 + severityScore * 0.6
```

**Issues:**
- Frontend uses severity-weighted incidents (backend doesn't)
- Frontend has a complex fallback calculation
- Different scaling approach

## 5. Response Time Factor

### Backend Calculation (line 987):
```python
response_time = min(10, (metrics.get("avg_response_time_minutes", 0) or 0) / 6)
```

### Frontend Calculation (lines 5470-5488):
```typescript
// Complex calculation based on thresholds
const avgResponseTime = m?.metrics?.avg_response_time_minutes || 0;

if (avgResponseTime >= 120) return 10;
else if (avgResponseTime >= 60) return 8 + ((avgResponseTime - 60) / 60) * 2;
else if (avgResponseTime >= 30) return 5 + ((avgResponseTime - 30) / 30) * 3;
else if (avgResponseTime >= 15) return 2.5 + ((avgResponseTime - 15) / 15) * 2.5;
else return avgResponseTime / 6;
```

**Issues:**
- Frontend uses threshold-based scaling
- Backend uses simple linear scaling (/6)
- Very different results for same input

## Summary of Key Issues:

1. **GitHub Activity Integration**: Frontend includes GitHub data in calculations, backend doesn't
2. **Different Scaling Formulas**: Almost every factor uses different math
3. **Severity Weighting**: Frontend considers severity, backend doesn't
4. **Fallback Logic**: Frontend has complex fallbacks, backend doesn't
5. **Time Period**: Frontend divides by 4.3 weeks, backend uses pre-calculated incidents_per_week

## Recommendation:

The frontend should NOT calculate these factors. It should only display the factors received from the backend API. The backend is the single source of truth for burnout calculations.