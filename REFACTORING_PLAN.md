# Refactoring Plan: unified_burnout_analyzer.py

## Executive Summary

**Current State**: 5,848 lines, 55 methods, difficult to maintain/test/extend

**Target State**: 17 focused classes across clean architecture

**Timeline**: 3-4 weeks incremental migration

**Risk**: Medium (mitigated by comprehensive testing)

---

## Current Problems

### Monster Methods
- `analyze_burnout()`: **950 lines**
- `_generate_daily_trends()`: **717 lines**
- `_analyze_member_burnout()`: **478 lines**

### Violations
- ❌ Single Responsibility Principle - does everything
- ❌ Open/Closed Principle - hard to extend
- ❌ Dependency Inversion - concrete dependencies everywhere
- ❌ God Object anti-pattern

### Impact
- Hard to test (30+ dependencies to mock)
- Hard to understand (days for new developers)
- Hard to extend (adding integration touches 10+ methods)
- Hard to debug (6000 lines to search)

---

## Proposed Architecture

```
UnifiedBurnoutAnalyzer (Orchestrator ~300 lines)
├── DataCollectionService (~250 lines)
├── IntegrationHub (~150 lines)
│   ├── GitHubIntegration (~300 lines)
│   ├── JiraIntegration (~300 lines)
│   ├── LinearIntegration (~200 lines)
│   └── SlackIntegration (~100 lines)
├── MetricsCalculator (~700 lines)
├── BurnoutScoringEngine (~350 lines)
│   ├── TraumaAnalyzer (~150 lines)
│   └── RecoveryAnalyzer (~120 lines)
├── DailyTrendsGenerator (~200 lines)
│   ├── TeamDailyAggregator (~300 lines)
│   └── IndividualDailyTracker (~300 lines)
├── TeamAnalysisService (~400 lines)
├── InsightsGenerator (~250 lines)
├── TimeUtilities (~150 lines)
└── PlatformAdapter (~250 lines)
```

**Total**: ~4,720 lines (down from 5,848)

---

## Class Breakdown

### 1. **DataCollectionService** (~250 lines)
**Responsibility**: Fetch and normalize data from Rootly/PagerDuty

**Methods**:
- `collect_analysis_data()` - Main entry point
- `fetch_users()` - Get team users
- `fetch_incidents()` - Get incident data
- `load_mock_scenario()` - Testing support
- `build_user_timezone_map()` - TZ mapping

**Benefits**:
- Isolates API client logic
- Easy to mock for testing
- Platform-agnostic interface

---

### 2. **IntegrationHub** (~900 lines total)
**Responsibility**: Manage external integrations

**Sub-components**:
- `GitHubIntegration` (300 lines) - Commit/PR analysis
- `JiraIntegration` (300 lines) - Ticket workload
- `LinearIntegration` (200 lines) - Issue tracking
- `SlackIntegration` (100 lines) - Communication patterns

**Interface**:
```python
class IntegrationHub:
    async def collect_all_integration_data(...) -> IntegrationData

class GitHubIntegration:
    async def collect_team_data(...) -> Dict
    def calculate_burnout_contribution(...) -> float
    def calculate_insights(...) -> Dict
```

**Benefits**:
- Each integration independently testable
- Easy to add new integrations
- Can disable without affecting core

---

### 3. **MetricsCalculator** (~700 lines)
**Responsibility**: Calculate metrics from raw data

**Methods**:
- `calculate_base_metrics()` - Incident-based metrics
- `enhance_with_github()` - Add GitHub activity
- `enhance_with_jira()` - Add workload metrics
- `calculate_confidence_intervals()` - Data quality

**Benefits**:
- Pure functions, easy to test
- Clear data enhancement pipeline
- Platform-agnostic

---

### 4. **BurnoutScoringEngine** (~600 lines total)
**Responsibility**: Copenhagen Burnout Inventory scoring

**Components**:
- `BurnoutScoringEngine` (350 lines) - Main OCH scoring
- `TraumaAnalyzer` (150 lines) - Compound trauma detection
- `RecoveryAnalyzer` (120 lines) - Recovery deficit calculation

**Interface**:
```python
class BurnoutScoringEngine:
    def calculate_burnout_score(...) -> BurnoutScore
    def calculate_personal_burnout(...) -> float
    def calculate_work_burnout(...) -> float
```

**Benefits**:
- Isolates complex scoring logic
- Research-based methodology self-contained
- Easy to test with fixtures

---

### 5. **DailyTrendsGenerator** (~750 lines total)
**Responsibility**: Time-series data generation

**Components**:
- `DailyTrendsGenerator` (200 lines) - Orchestrator
- `TeamDailyAggregator` (300 lines) - Team-level aggregation
- `IndividualDailyTracker` (300 lines) - Individual tracking

**Benefits**:
- 718-line method broken into logical components
- Team vs individual clearly separated
- Easier to add new time-series data

---

### 6. **TeamAnalysisService** (~400 lines)
**Responsibility**: Team-level orchestration

**Methods**:
- `analyze_team()` - Main team analysis
- `analyze_member()` - Single member analysis
- `calculate_team_health()` - Aggregate team metrics
- `map_user_incidents()` - User-incident correlation

**Benefits**:
- Delegates to specialized services
- Focuses on orchestration
- Clear team-level logic

---

### 7. **InsightsGenerator** (~250 lines)
**Responsibility**: Insights and recommendations

**Methods**:
- `generate_insights()` - Pattern detection
- `generate_recommendations()` - Actionable items
- `enhance_with_ai()` - Optional AI enhancement

**Benefits**:
- AI enhancement isolated
- Clear insight patterns
- Easy to extend

---

### 8. **TimeUtilities** (~150 lines)
**Responsibility**: Time and timezone logic

**Methods**:
- `get_user_timezone()`
- `parse_iso_timestamp()`
- `to_local_time()`
- `is_after_hours()`
- `is_weekend()`

**Benefits**:
- All time logic centralized
- Easy timezone testing
- Configurable business hours

---

### 9. **PlatformAdapter** (~250 lines)
**Responsibility**: Abstract platform differences

**Methods**:
- `extract_incident_title()`
- `get_severity_level()`
- `compare_severity()`
- `extract_response_time()`
- `normalize_incident()`

**Benefits**:
- Single place for platform logic
- Easy to add new platforms
- Clear abstraction layer

---

### 10. **UnifiedBurnoutAnalyzer** (~300 lines)
**Responsibility**: Main orchestration

**Refactored to**:
- Initialize dependencies
- Orchestrate analysis flow
- Assemble results
- Handle errors

**From 950 lines → 300 lines**

---

## Migration Strategy

### Phase 1: Extract Utilities (Low Risk) - 1-2 days
- TimeUtilities
- PlatformAdapter
- ✅ No dependencies, pure functions

### Phase 2: Extract Data Layer (Medium Risk) - 2-3 days
- DataCollectionService
- MetricsCalculator
- ✅ Test with real data

### Phase 3: Extract Scoring Engine (Medium Risk) - 2-3 days
- BurnoutScoringEngine + sub-analyzers
- ✅ Snapshot testing for scores

### Phase 4: Extract Integrations (Medium-High Risk) - 3-4 days
- GitHubIntegration, JiraIntegration, LinearIntegration
- IntegrationHub
- ✅ Test correlation logic

### Phase 5: Extract Analysis Services (High Risk) - 3-4 days
- TeamAnalysisService
- DailyTrendsGenerator
- InsightsGenerator
- ✅ Full end-to-end tests

### Phase 6: Finalize Orchestrator (Medium Risk) - 2-3 days
- Refactor `analyze_burnout()`
- Update imports
- Documentation
- ✅ Full regression suite

**Total**: 3-4 weeks incremental migration

---

## Testing Strategy

### Regression Testing (Critical)
```python
# Golden dataset approach
test_score_regression.py
  - 100 real analyses as baseline
  - Compare old vs new scores
  - Assert < 0.1% deviation
```

### Unit Tests
- 240+ tests across all classes
- 85%+ coverage target
- Pure function testing

### Integration Tests
- Component interaction tests
- Platform-specific tests
- External API mocking

### End-to-End Tests
- Full analysis pipeline
- Multiple scenarios
- Performance benchmarking

---

## Risks & Mitigation

### Risk 1: Breaking Functionality
**Mitigation**: Feature flags, comprehensive tests, gradual rollout

### Risk 2: OCH Score Changes
**Mitigation**: Golden dataset testing, stakeholder approval

### Risk 3: Performance Regression
**Mitigation**: Profile before/after, minimize object creation

### Risk 4: Timezone Logic Breakage
**Mitigation**: Comprehensive timezone tests, edge cases

### Risk 5: Daily Trends Complexity
**Mitigation**: Refactor in small chunks, validate JSON output

---

## Success Metrics

### Code Quality
- ✅ Cyclomatic complexity < 10 per method
- ✅ Test coverage > 85%
- ✅ No class > 500 lines
- ✅ No method > 100 lines

### Functional
- ✅ OCH score deviation < 0.1%
- ✅ Performance within 5% of baseline
- ✅ No integration regressions

### Developer Experience
- ✅ New dev understands flow in < 4 hours
- ✅ Bug fix time 30% faster
- ✅ New integrations < 2 days

---

## File Structure

```
backend/app/services/burnout/
├── __init__.py
├── orchestrator.py (UnifiedBurnoutAnalyzer)
├── data_collection.py
├── metrics_calculator.py
├── scoring/
│   ├── __init__.py
│   ├── engine.py
│   ├── trauma_analyzer.py
│   └── recovery_analyzer.py
├── integrations/
│   ├── __init__.py
│   ├── hub.py
│   ├── github_integration.py
│   ├── jira_integration.py
│   ├── linear_integration.py
│   └── slack_integration.py
├── analysis/
│   ├── __init__.py
│   ├── team_service.py
│   ├── daily_trends.py
│   └── insights.py
└── utils/
    ├── __init__.py
    ├── time_utils.py
    └── platform_adapter.py
```

---

## Benefits

### Maintainability
- **Before**: Search 6,000 lines for logic
- **After**: Look in specific class (~300 lines)

### Testability
- **Before**: Mock 30+ dependencies
- **After**: Test pure functions, no mocks

### Extensibility
- **Before**: Touch 10+ methods for new integration
- **After**: Create new integration class

### Understandability
- **Before**: Days to understand flow
- **After**: Clear service hierarchy

### Performance
- **Before**: Hard to profile
- **After**: Profile individual services

---

## Next Steps

1. **Review with team** (1-2 days)
2. **Create test baseline** (3-5 days)
3. **Start Phase 1** (utilities)
4. **Weekly progress reviews**
5. **Monitor production closely**

---

## Conclusion

**Effort**: 3-4 weeks

**Risk**: Medium (with proper testing)

**ROI**: High - 40% faster maintenance, better code quality

This refactoring transforms a 5,848-line monolith into a clean, maintainable architecture following SOLID principles.
