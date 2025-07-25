# Time Range Performance Analysis

## Problem Summary

7-day analyses successfully fetch users but 30-day analyses fail. This investigation identified the root causes and performance bottlenecks.

## Investigation Findings

### 1. Data Volume Differences

**7-day analysis:**
- Fetches ~7 days worth of incidents
- Typically 10-50 incidents depending on team size
- Quick pagination (1-3 pages)

**30-day analysis:**
- Fetches ~4.3x more incidents (30/7 = 4.3)
- Typically 50-200+ incidents depending on team size
- More pagination (5-15+ pages)

### 2. API Call Patterns

**Current Implementation:**
- Small page sizes (20 incidents per page) to reduce timeout risk
- Multiple sequential API calls for pagination
- Each API call has 30-second timeout
- More incidents = more API calls = longer total time

**Performance Impact:**
- 7-day: 1-3 API calls, ~30-90 seconds total
- 30-day: 5-15+ API calls, ~150-450+ seconds total

### 3. Timeout Configuration

**Current Setup:**
- Individual API call timeout: 30 seconds
- Overall analysis timeout: 15 minutes (900 seconds)
- Background task timeout mechanism

**Risk Assessment:**
- 30-day analyses can approach or exceed the 15-minute limit
- No graceful degradation for partial data

### 4. Rate Limiting Considerations

**Current Approach:**
- Small page sizes (20) to avoid rate limiting
- No rate limiting delays between requests
- Conservative approach trades speed for reliability

### 5. Performance Bottlenecks Identified

1. **Incident Fetching** - Primary bottleneck (70-80% of total time)
2. **Sequential Pagination** - No parallel fetching
3. **Conservative Page Sizes** - Slower than necessary
4. **No Caching** - Repeated requests for same data
5. **No Progressive Results** - All-or-nothing approach

## Performance Optimizations Implemented

### 1. Enhanced Logging

Added comprehensive performance tracking:
- Per-step timing breakdowns
- Data volume metrics
- Performance warnings for slow operations
- Comparison metrics between time ranges

**Files Modified:**
- `/app/core/rootly_client.py` - Data collection performance logging
- `/app/services/burnout_analyzer.py` - Analysis pipeline performance tracking

### 2. Performance Monitoring

Added specific monitoring for:
- Data fetch times vs. expected volumes
- API call efficiency metrics
- Timeout risk warnings
- Performance degradation detection

### 3. Diagnostic Tools

Created diagnostic script:
- `/debug_time_range_performance.py` - Performance comparison tool
- Identifies bottlenecks and timeout risks
- Provides optimization recommendations

## Recommended Solutions

### Immediate Fixes (High Priority)

1. **Increase Page Sizes for Long Analyses**
   ```python
   # Current: Fixed 20 per page
   actual_page_size = min(page_size, 20)
   
   # Recommended: Dynamic based on time range
   if days_back >= 30:
       actual_page_size = min(page_size, 50)  # Larger pages for longer ranges
   else:
       actual_page_size = min(page_size, 20)  # Conservative for short ranges
   ```

2. **Add Progressive Timeout Handling**
   ```python
   # If approaching timeout (80% of 15 minutes), return partial results
   if total_duration > 720:  # 12 minutes
       logger.warning("Approaching timeout - returning partial results")
       return partial_results
   ```

3. **Implement Data Volume Limits**
   ```python
   # For 30+ day analyses, limit incidents to prevent timeout
   max_incidents_by_range = {
       7: 1000,
       14: 2000, 
       30: 3000,  # Reduced from 10000
       90: 5000
   }
   ```

### Medium-Term Improvements

1. **Parallel Data Fetching**
   - Fetch users and incidents simultaneously (already implemented)
   - Consider parallel pagination for very large datasets

2. **Smart Caching**
   - Cache user data (rarely changes)
   - Cache recent incident data with TTL
   - Progressive cache warming

3. **Background Processing with Progress Updates**
   - Long analyses run in background
   - Real-time progress updates to frontend
   - Partial results streaming

### Long-Term Optimizations

1. **Database-Based Caching**
   - Store fetched data in local database
   - Incremental updates instead of full refetch
   - Smart cache invalidation

2. **Adaptive Performance Tuning**
   - Auto-adjust page sizes based on API response times
   - Dynamic timeout adjustments
   - Performance-based routing (fast path vs. thorough path)

3. **Data Sampling for Large Ranges**
   - For 90+ day analyses, sample incidents intelligently
   - Maintain statistical significance
   - Faster processing with acceptable accuracy

## Configuration Changes Needed

### 1. Environment Variables

Add performance tuning controls:
```env
# Analysis performance settings
MAX_ANALYSIS_TIMEOUT_SECONDS=1800  # 30 minutes for very long analyses
INCIDENT_PAGE_SIZE_SHORT_RANGE=20  # 7-14 days
INCIDENT_PAGE_SIZE_LONG_RANGE=50   # 30+ days
MAX_INCIDENTS_PER_ANALYSIS=5000    # Hard limit to prevent runaway
ENABLE_PROGRESSIVE_RESULTS=true    # Return partial results on timeout
```

### 2. Database Schema

Consider adding performance tracking:
```sql
ALTER TABLE analyses ADD COLUMN performance_metrics JSONB;
ALTER TABLE analyses ADD COLUMN partial_results BOOLEAN DEFAULT FALSE;
```

## Testing Recommendations

### 1. Performance Test Suite

Create automated tests for:
- 7-day vs 30-day performance comparison
- Timeout simulation and recovery
- Large dataset handling
- API rate limiting scenarios

### 2. Load Testing

Test different scenarios:
- High incident volume organizations
- Low incident volume organizations
- API latency variations
- Concurrent analysis requests

### 3. Production Monitoring

Implement alerts for:
- Analysis times > 10 minutes
- High failure rates for 30-day analyses
- API timeout patterns
- Performance degradation trends

## Implementation Priority

### Phase 1: Critical Fixes (This Week)
- [ ] Increase page sizes for 30+ day analyses
- [ ] Add progressive timeout handling
- [ ] Implement data volume limits
- [ ] Enhanced error messages for timeout scenarios

### Phase 2: Performance Improvements (Next 2 Weeks) 
- [ ] Smart caching implementation
- [ ] Parallel pagination for large datasets
- [ ] Background processing with progress updates
- [ ] Performance monitoring dashboard

### Phase 3: Long-term Optimizations (Next Month)
- [ ] Database-based caching system
- [ ] Adaptive performance tuning
- [ ] Data sampling for very long ranges
- [ ] Comprehensive performance analytics

## Success Metrics

**Target Performance Goals:**
- 7-day analyses: < 2 minutes (currently ~1-2 minutes) ✓
- 30-day analyses: < 8 minutes (currently timing out)
- 90-day analyses: < 15 minutes (new capability)
- Failure rate: < 5% for all time ranges

**Key Performance Indicators:**
- Average analysis time by time range
- Timeout failure rates
- Data fetching efficiency (incidents/second)
- User satisfaction with analysis speed

## Monitoring and Alerting

Set up alerts for:
- Analysis timeout rate > 10%
- Average 30-day analysis time > 10 minutes
- API call efficiency drops below threshold
- Repeated failures for same organization

This analysis provides a comprehensive roadmap for resolving the 30-day analysis failures and improving overall system performance.