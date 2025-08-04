# Burnout Factor Calculation Fix Summary

## Problem
The frontend was calculating burnout factors independently instead of using the backend's calculations, causing data inconsistencies across the dashboard.

## Key Issues Found

### 1. Different Calculation Formulas
- **Workload**: Frontend used `incidents * 0.4` capped at 5, backend uses tiered scaling
- **After Hours**: Frontend included GitHub activity, backend only considers incidents
- **Response Time**: Frontend used threshold-based scaling, backend uses linear `/6`
- **Weekend Work**: Frontend combined GitHub + incident data, backend only incidents
- **Incident Load**: Frontend used severity weighting, backend uses incident count

### 2. Data Sources
- Frontend was trying to combine GitHub activity with incident data
- Backend only uses incident data for factor calculations
- This caused inflated scores for developers with high GitHub activity

### 3. Time Period Differences
- Frontend divided by 4.3 weeks
- Backend uses pre-calculated `incidents_per_week` from the analyzer

## Solution Implemented

### 1. Member Modal Factors (lines 5384-5415)
Replaced complex calculation logic with simple backend value usage:
```typescript
// Before: 100+ lines of calculations
// After: Direct backend value usage
const memberFactors = [
  {
    factor: 'Workload Intensity',
    value: m?.factors?.workload ?? 0.1,
    color: '#FF6B6B'
  },
  // ... other factors similarly simplified
];
```

### 2. Organization-Level Factors (lines 2319-2408)
Changed from recalculating to averaging backend factors:
```typescript
// Before: Complex member-by-member recalculation
// After: Simple average of backend factors
const workloadScores = allActiveMembers
  .map((m: any) => m?.factors?.workload ?? 0)
  .filter(score => score > 0);

const sum = workloadScores.reduce((total, score) => total + score, 0);
return Number((sum / workloadScores.length).toFixed(1));
```

## Impact
- Burnout factor charts now show exactly what the backend calculated
- No more discrepancies between different parts of the dashboard
- Consistent data throughout the application
- Simpler, more maintainable code

## Files Modified
- `/frontend/src/app/dashboard/page.tsx` - Removed all duplicate factor calculations
- `/burnout-factor-comparison.md` - Documentation of differences found

## Principle Established
**The backend is the single source of truth for all burnout calculations. The frontend should only display data, never recalculate it.**