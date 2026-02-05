# MCP Server Tests

Comprehensive unit tests for the On-Call Health MCP server.

## Test Coverage

### Helper Functions (`TestHelperFunctions`)
- `_validate_analysis_id`: Tests positive, zero, and negative IDs
- `_validate_api_key`: Tests with and without API keys

### Bug Fix Verification (`TestAnalysisSummary`)
- Verifies `analysis_summary` reads from correct path (`team_analysis.members`)
- Tests with empty members list
- **Bug fixed**: Changed from `.get("members")` to `.get("team_analysis", {}).get("members")`

### New Tool: get_at_risk_users (`TestGetAtRiskUsers`)
- Default parameters (min_och_score=50.0, medium/high risk levels)
- Custom OCH score threshold
- Risk level filtering (high only)
- Case-insensitive risk levels (HIGH vs high)
- Empty results
- External ID inclusion (Rootly, PagerDuty, Slack, GitHub)
- **Edge cases:** Missing analysis_data, missing team_analysis, missing members

### New Tool: get_safe_responders (`TestGetSafeResponders`)
- Default parameters (max_och_score=30.0, limit=10)
- Custom OCH score threshold
- Limit parameter enforcement
- Empty results
- **Edge case:** Missing analysis_data

### New Tool: check_users_risk (`TestCheckUsersRisk`)
- Mixed results (at_risk, healthy, not_found)
- Custom min_och_score threshold
- Risk level override (medium/high overrides score)
- Exact threshold boundary (>= behavior)
- Invalid ID format handling
- Empty ID string validation
- Integer overflow protection (32-bit bounds)
- All IDs not found scenario
- **Edge case:** Missing analysis_data

### Validation Errors (`TestValidationErrors`)
- All tools reject invalid analysis_id
- All tools reject missing API key

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with coverage
```bash
pytest tests/ --cov=oncallhealth_mcp --cov-report=term-missing
```

### Run specific test class
```bash
pytest tests/test_server.py::TestGetAtRiskUsers -v
```

### Run specific test
```bash
pytest tests/test_server.py::TestGetAtRiskUsers::test_get_at_risk_users_default_params -v
```

## Test Fixtures

### `mock_context` (conftest.py)
Mock context object with API key for testing.

### `sample_analysis_response` (conftest.py)
Sample API response with 5 test users:
- **Quentin Rousseau**: och_score=72.5, risk_level=high
- **Alice Johnson**: och_score=12.3, risk_level=low
- **Bob Smith**: och_score=55.0, risk_level=medium
- **Carol Davis**: och_score=25.0, risk_level=low
- **Diana Prince**: och_score=68.0, risk_level=HIGH (case test)

### `sample_analysis_summary_response` (conftest.py)
Simplified response for testing analysis_summary bug fix.

## Test Results

```
================================ tests coverage ================================
src/oncallhealth_mcp/server.py                     251    102    59%
------------------------------------------------------------------------------
32 passed in 0.52s
```

### Coverage Focus
- ✅ Helper functions: 100%
- ✅ Bug fix (analysis_summary): 100%
- ✅ New tool (get_at_risk_users): 100%
- ✅ New tool (get_safe_responders): 100%
- ✅ New tool (check_users_risk): 100%

### Uncovered Lines
Lines not covered are primarily:
- Other existing tools (not modified in this PR)
- Error handling paths for exceptional cases
- Integration points with external services

## Mocking Strategy

Tests use proper async mocking for:
- `OnCallHealthClient`: Async context manager
- `client.get()`: Async method returning httpx.Response
- `response.json()`: Synchronous method returning data dict

Example:
```python
mock_response = MagicMock()
mock_response.json.return_value = sample_data

mock_client = AsyncMock()
mock_client.get.return_value = mock_response
mock_client.__aenter__.return_value = mock_client
mock_client.__aexit__.return_value = None
```

## CI/CD Integration

Add to GitHub Actions workflow:
```yaml
- name: Run tests
  run: |
    cd packages/oncallhealth-mcp
    pip install -e ".[test]"
    pytest tests/ -v --cov=oncallhealth_mcp
```
