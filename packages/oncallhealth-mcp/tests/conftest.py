"""Pytest fixtures for MCP server tests."""
import pytest
from typing import Any, Dict, List


@pytest.fixture
def mock_context():
    """Mock context object with API key."""
    class MockContext:
        def __init__(self, api_key: str = "test-api-key"):
            self.api_key = api_key
            self.headers = {"X-API-Key": api_key}

    return MockContext()


@pytest.fixture
def mock_context_no_key():
    """Mock context object without API key."""
    class MockContext:
        def __init__(self):
            self.api_key = None
            self.headers = {}

    return MockContext()


@pytest.fixture
def sample_analysis_response() -> Dict[str, Any]:
    """Sample API response for analysis endpoint."""
    return {
        "id": 1226,
        "status": "completed",
        "analysis_data": {
            "team_analysis": {
                "members": [
                    {
                        "user_id": "001",
                        "user_name": "Quentin Rousseau",
                        "user_email": "quentin@example.com",
                        "och_score": 72.5,
                        "risk_level": "high",
                        "burnout_score": 68.2,
                        "incident_count": 45,
                        "rootly_user_id": 2381,
                        "pagerduty_user_id": "P123ABC",
                        "slack_user_id": "U012345",
                        "github_username": "quentinr"
                    },
                    {
                        "user_id": "002",
                        "user_name": "Alice Johnson",
                        "user_email": "alice@example.com",
                        "och_score": 12.3,
                        "risk_level": "low",
                        "burnout_score": 10.5,
                        "incident_count": 15,
                        "rootly_user_id": 94178,
                        "slack_user_id": "U789XYZ"
                    },
                    {
                        "user_id": "003",
                        "user_name": "Bob Smith",
                        "user_email": "bob@example.com",
                        "och_score": 55.0,
                        "risk_level": "medium",
                        "burnout_score": 52.0,
                        "incident_count": 30,
                        "rootly_user_id": 1234,
                        "pagerduty_user_id": "P456DEF"
                    },
                    {
                        "user_id": "004",
                        "user_name": "Carol Davis",
                        "user_email": "carol@example.com",
                        "och_score": 25.0,
                        "risk_level": "low",
                        "burnout_score": 22.0,
                        "incident_count": 20,
                        "rootly_user_id": 5678
                    },
                    {
                        "user_id": "005",
                        "user_name": "Diana Prince",
                        "user_email": "diana@example.com",
                        "och_score": 68.0,
                        "risk_level": "HIGH",  # Test case-insensitivity
                        "burnout_score": 65.0,
                        "incident_count": 40,
                        "rootly_user_id": 9101
                    }
                ]
            }
        }
    }


@pytest.fixture
def sample_analysis_summary_response() -> Dict[str, Any]:
    """Sample API response for analysis summary."""
    return {
        "id": 1226,
        "status": "completed",
        "created_at": "2024-02-04T10:00:00Z",
        "analysis_data": {
            "team_analysis": {
                "members": [
                    {"user_id": "001", "user_name": "User 1", "cbi_score": 70},
                    {"user_id": "002", "user_name": "User 2", "cbi_score": 30},
                ]
            },
            "team_health": {
                "overall_score": 50.0,
                "risk_distribution": {
                    "low": 1,
                    "medium": 0,
                    "high": 1,
                    "critical": 0
                }
            }
        }
    }
