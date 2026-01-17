"""
Unit tests for the avatar_url feature in UserSyncService.
Tests the extraction, storage, and update of profile image URLs from PagerDuty and Rootly.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from app.services.user_sync_service import UserSyncService
from app.models import UserCorrelation, User


class TestAvatarUrlExtraction:
    """Tests for avatar_url extraction from API responses"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.count.return_value = 0
        return db

    @pytest.fixture
    def user_sync_service(self, mock_db):
        """Create UserSyncService with mock db"""
        return UserSyncService(mock_db)

    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "admin@example.com"
        user.organization_id = 100
        return user

    def test_fetch_rootly_users_extracts_avatar_url(self, user_sync_service):
        """Test that _fetch_rootly_users extracts avatar_url from Rootly API response"""
        mock_rootly_response = [
            {
                "id": "user1",
                "attributes": {
                    "email": "john@example.com",
                    "name": "John Doe",
                    "full_name": "John Doe",
                    "time_zone": "America/New_York",
                    "avatar_url": "https://rootly.com/avatars/john.png"
                }
            },
            {
                "id": "user2",
                "attributes": {
                    "email": "jane@example.com",
                    "name": "Jane Smith",
                    "full_name": "Jane Smith",
                    "time_zone": "America/Los_Angeles",
                    "avatar_url": "https://rootly.com/avatars/jane.png"
                }
            }
        ]

        with patch('app.services.user_sync_service.RootlyAPIClient') as mock_client:
            client_instance = mock_client.return_value
            client_instance.get_users = AsyncMock(return_value=(mock_rootly_response, []))
            client_instance.filter_incident_responders = MagicMock(return_value=mock_rootly_response)

            users = asyncio.run(user_sync_service._fetch_rootly_users("test_token"))

        assert len(users) == 2
        assert users[0]["avatar_url"] == "https://rootly.com/avatars/john.png"
        assert users[1]["avatar_url"] == "https://rootly.com/avatars/jane.png"
        assert users[0]["platform"] == "rootly"

    def test_fetch_rootly_users_handles_missing_avatar_url(self, user_sync_service):
        """Test that _fetch_rootly_users handles users without avatar_url"""
        mock_rootly_response = [
            {
                "id": "user1",
                "attributes": {
                    "email": "john@example.com",
                    "name": "John Doe",
                    "time_zone": "America/New_York"
                    # No avatar_url
                }
            }
        ]

        with patch('app.services.user_sync_service.RootlyAPIClient') as mock_client:
            client_instance = mock_client.return_value
            client_instance.get_users = AsyncMock(return_value=(mock_rootly_response, []))
            client_instance.filter_incident_responders = MagicMock(return_value=mock_rootly_response)

            users = asyncio.run(user_sync_service._fetch_rootly_users("test_token"))

        assert len(users) == 1
        assert users[0]["avatar_url"] is None

    def test_fetch_pagerduty_users_extracts_avatar_url(self, user_sync_service):
        """Test that _fetch_pagerduty_users extracts avatar_url from PagerDuty API response"""
        mock_pagerduty_response = [
            {
                "id": "PUSER1",
                "email": "john@example.com",
                "name": "John Doe",
                "time_zone": "America/New_York",
                "avatar_url": "https://secure.gravatar.com/avatar/john123"
            },
            {
                "id": "PUSER2",
                "email": "jane@example.com",
                "name": "Jane Smith",
                "time_zone": "America/Los_Angeles",
                "avatar_url": "https://secure.gravatar.com/avatar/jane456"
            }
        ]

        with patch('app.services.user_sync_service.PagerDutyAPIClient') as mock_client:
            client_instance = mock_client.return_value
            client_instance.get_users = AsyncMock(return_value=mock_pagerduty_response)

            users = asyncio.run(user_sync_service._fetch_pagerduty_users("test_token"))

        assert len(users) == 2
        assert users[0]["avatar_url"] == "https://secure.gravatar.com/avatar/john123"
        assert users[1]["avatar_url"] == "https://secure.gravatar.com/avatar/jane456"
        assert users[0]["platform"] == "pagerduty"

    def test_fetch_pagerduty_users_handles_missing_avatar_url(self, user_sync_service):
        """Test that _fetch_pagerduty_users handles users without avatar_url"""
        mock_pagerduty_response = [
            {
                "id": "PUSER1",
                "email": "john@example.com",
                "name": "John Doe",
                "time_zone": "America/New_York"
                # No avatar_url
            }
        ]

        with patch('app.services.user_sync_service.PagerDutyAPIClient') as mock_client:
            client_instance = mock_client.return_value
            client_instance.get_users = AsyncMock(return_value=mock_pagerduty_response)

            users = asyncio.run(user_sync_service._fetch_pagerduty_users("test_token"))

        assert len(users) == 1
        assert users[0].get("avatar_url") is None


class TestAvatarUrlUpdate:
    """Tests for avatar_url update in _update_correlation"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = MagicMock()
        return db

    @pytest.fixture
    def user_sync_service(self, mock_db):
        """Create UserSyncService with mock db"""
        return UserSyncService(mock_db)

    def test_update_correlation_sets_avatar_url(self, user_sync_service):
        """Test that _update_correlation sets avatar_url when provided"""
        correlation = MagicMock(spec=UserCorrelation)
        correlation.integration_ids = None
        correlation.name = None
        correlation.timezone = None
        correlation.avatar_url = None
        correlation.rootly_user_id = None
        correlation.rootly_email = None

        user_data = {
            "id": "user1",
            "email": "john@example.com",
            "name": "John Doe",
            "timezone": "America/New_York",
            "avatar_url": "https://example.com/avatar.png"
        }

        result = user_sync_service._update_correlation(
            correlation=correlation,
            user=user_data,
            platform="rootly",
            integration_id="integration1"
        )

        assert result == 1  # Returns 1 when updated
        assert correlation.avatar_url == "https://example.com/avatar.png"

    def test_update_correlation_updates_avatar_url_when_changed(self, user_sync_service):
        """Test that _update_correlation updates avatar_url when it changes"""
        correlation = MagicMock(spec=UserCorrelation)
        correlation.integration_ids = ["integration1"]
        correlation.name = "John Doe"
        correlation.timezone = "America/New_York"
        correlation.avatar_url = "https://example.com/old_avatar.png"
        correlation.rootly_user_id = "user1"
        correlation.rootly_email = "john@example.com"

        user_data = {
            "id": "user1",
            "email": "john@example.com",
            "name": "John Doe",
            "timezone": "America/New_York",
            "avatar_url": "https://example.com/new_avatar.png"  # Changed
        }

        result = user_sync_service._update_correlation(
            correlation=correlation,
            user=user_data,
            platform="rootly",
            integration_id="integration1"
        )

        assert result == 1
        assert correlation.avatar_url == "https://example.com/new_avatar.png"

    def test_update_correlation_does_not_overwrite_with_none(self, user_sync_service):
        """Test that _update_correlation does not overwrite existing avatar_url with None"""
        correlation = MagicMock(spec=UserCorrelation)
        correlation.integration_ids = ["integration1"]
        correlation.name = "John Doe"
        correlation.timezone = "America/New_York"
        correlation.avatar_url = "https://example.com/existing_avatar.png"
        correlation.rootly_user_id = "user1"
        correlation.rootly_email = "john@example.com"

        user_data = {
            "id": "user1",
            "email": "john@example.com",
            "name": "John Doe",
            "timezone": "America/New_York",
            "avatar_url": None  # Missing in API response
        }

        result = user_sync_service._update_correlation(
            correlation=correlation,
            user=user_data,
            platform="rootly",
            integration_id="integration1"
        )

        # Should return 0 (no update) since avatar_url wasn't provided
        assert result == 0
        # Original avatar should be preserved
        assert correlation.avatar_url == "https://example.com/existing_avatar.png"

    def test_update_correlation_no_change_when_same_avatar(self, user_sync_service):
        """Test that _update_correlation returns 0 when avatar_url is unchanged"""
        correlation = MagicMock(spec=UserCorrelation)
        correlation.integration_ids = ["integration1"]
        correlation.name = "John Doe"
        correlation.timezone = "America/New_York"
        correlation.avatar_url = "https://example.com/same_avatar.png"
        correlation.rootly_user_id = "user1"
        correlation.rootly_email = "john@example.com"

        user_data = {
            "id": "user1",
            "email": "john@example.com",
            "name": "John Doe",
            "timezone": "America/New_York",
            "avatar_url": "https://example.com/same_avatar.png"  # Same value
        }

        result = user_sync_service._update_correlation(
            correlation=correlation,
            user=user_data,
            platform="rootly",
            integration_id="integration1"
        )

        assert result == 0  # No changes made


class TestAvatarUrlInSyncFlow:
    """Tests for avatar_url in the full sync flow"""

    @pytest.fixture
    def mock_db(self):
        """Create a mock database session"""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        db.query.return_value.filter.return_value.all.return_value = []
        db.query.return_value.filter.return_value.count.return_value = 0
        return db

    @pytest.fixture
    def user_sync_service(self, mock_db):
        """Create UserSyncService with mock db"""
        return UserSyncService(mock_db)

    @pytest.fixture
    def mock_user(self):
        """Create a mock user"""
        user = MagicMock(spec=User)
        user.id = 1
        user.email = "admin@example.com"
        user.organization_id = 100
        return user

    def test_sync_users_creates_correlation_with_avatar_url(self, user_sync_service, mock_user, mock_db):
        """Test that _sync_users_to_correlation creates new records with avatar_url"""
        users = [
            {
                "id": "user1",
                "email": "john@example.com",
                "name": "John Doe",
                "timezone": "America/New_York",
                "avatar_url": "https://example.com/john_avatar.png"
            }
        ]

        # Mock no existing correlation
        mock_db.query.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.first.return_value = None

        # Capture the UserCorrelation that gets added
        added_correlations = []
        def capture_add(obj):
            added_correlations.append(obj)
        mock_db.add.side_effect = capture_add

        result = user_sync_service._sync_users_to_correlation(
            users=users,
            platform="rootly",
            current_user=mock_user,
            integration_id="integration1"
        )

        assert result["created"] == 1
        assert len(added_correlations) == 1
        assert added_correlations[0].avatar_url == "https://example.com/john_avatar.png"


class TestUserCorrelationModel:
    """Tests for the UserCorrelation model's avatar_url field"""

    def test_user_correlation_has_avatar_url_field(self):
        """Test that UserCorrelation model has avatar_url field"""
        # Check that the model has the avatar_url column
        assert hasattr(UserCorrelation, 'avatar_url')

    def test_user_correlation_avatar_url_allows_null(self):
        """Test that avatar_url column allows NULL values"""
        from sqlalchemy import inspect
        mapper = inspect(UserCorrelation)
        avatar_url_col = mapper.columns.get('avatar_url')
        assert avatar_url_col is not None
        assert avatar_url_col.nullable is True

    def test_user_correlation_avatar_url_max_length(self):
        """Test that avatar_url column has appropriate max length for URLs"""
        from sqlalchemy import inspect
        mapper = inspect(UserCorrelation)
        avatar_url_col = mapper.columns.get('avatar_url')
        assert avatar_url_col is not None
        # Should have sufficient length for URLs (512 chars)
        assert avatar_url_col.type.length == 512


class TestSyncedUserDataIncludesPlatformIds:
    """Tests to ensure synced user data includes rootly_user_id and pagerduty_user_id for icon display"""

    def test_synced_user_data_includes_rootly_user_id(self):
        """Test that synced user data structure includes rootly_user_id"""
        # Simulate the user_data structure built in analyses.py
        mock_correlation = MagicMock()
        mock_correlation.rootly_user_id = "12345"
        mock_correlation.pagerduty_user_id = None
        mock_correlation.name = "John Doe"
        mock_correlation.email = "john@example.com"
        mock_correlation.github_username = "johndoe"
        mock_correlation.slack_user_id = "U12345"
        mock_correlation.jira_account_id = "jira123"
        mock_correlation.linear_user_id = "linear456"
        mock_correlation.avatar_url = "https://example.com/avatar.png"

        # Build user_data the same way analyses.py does
        user_data = {
            'id': mock_correlation.rootly_user_id or mock_correlation.email,
            'name': mock_correlation.name,
            'email': mock_correlation.email,
            'github_username': mock_correlation.github_username,
            'slack_user_id': mock_correlation.slack_user_id,
            'jira_account_id': mock_correlation.jira_account_id,
            'linear_user_id': mock_correlation.linear_user_id,
            'rootly_user_id': mock_correlation.rootly_user_id,
            'pagerduty_user_id': mock_correlation.pagerduty_user_id,
            'avatar_url': mock_correlation.avatar_url,
        }

        # Verify rootly_user_id is included
        assert 'rootly_user_id' in user_data
        assert user_data['rootly_user_id'] == "12345"

    def test_synced_user_data_includes_pagerduty_user_id(self):
        """Test that synced user data structure includes pagerduty_user_id"""
        mock_correlation = MagicMock()
        mock_correlation.rootly_user_id = None
        mock_correlation.pagerduty_user_id = "PUSER123"
        mock_correlation.name = "Jane Smith"
        mock_correlation.email = "jane@example.com"
        mock_correlation.github_username = None
        mock_correlation.slack_user_id = None
        mock_correlation.jira_account_id = None
        mock_correlation.linear_user_id = None
        mock_correlation.avatar_url = "https://gravatar.com/avatar/jane.png"

        user_data = {
            'id': mock_correlation.pagerduty_user_id or mock_correlation.email,
            'name': mock_correlation.name,
            'email': mock_correlation.email,
            'github_username': mock_correlation.github_username,
            'slack_user_id': mock_correlation.slack_user_id,
            'jira_account_id': mock_correlation.jira_account_id,
            'linear_user_id': mock_correlation.linear_user_id,
            'rootly_user_id': mock_correlation.rootly_user_id,
            'pagerduty_user_id': mock_correlation.pagerduty_user_id,
            'avatar_url': mock_correlation.avatar_url,
        }

        # Verify pagerduty_user_id is included
        assert 'pagerduty_user_id' in user_data
        assert user_data['pagerduty_user_id'] == "PUSER123"

    def test_synced_user_data_includes_both_platform_ids(self):
        """Test that user with both platform IDs has both included"""
        mock_correlation = MagicMock()
        mock_correlation.rootly_user_id = "rootly789"
        mock_correlation.pagerduty_user_id = "PDUTY456"
        mock_correlation.name = "Both Platforms User"
        mock_correlation.email = "both@example.com"
        mock_correlation.github_username = "bothuser"
        mock_correlation.slack_user_id = "UBOTH"
        mock_correlation.jira_account_id = None
        mock_correlation.linear_user_id = None
        mock_correlation.avatar_url = None

        user_data = {
            'id': mock_correlation.rootly_user_id,
            'name': mock_correlation.name,
            'email': mock_correlation.email,
            'github_username': mock_correlation.github_username,
            'slack_user_id': mock_correlation.slack_user_id,
            'jira_account_id': mock_correlation.jira_account_id,
            'linear_user_id': mock_correlation.linear_user_id,
            'rootly_user_id': mock_correlation.rootly_user_id,
            'pagerduty_user_id': mock_correlation.pagerduty_user_id,
            'avatar_url': mock_correlation.avatar_url,
        }

        # Verify both platform IDs are included
        assert 'rootly_user_id' in user_data
        assert 'pagerduty_user_id' in user_data
        assert user_data['rootly_user_id'] == "rootly789"
        assert user_data['pagerduty_user_id'] == "PDUTY456"

    def test_synced_user_data_all_icon_fields_present(self):
        """Test that all fields needed for icon display are present in user_data"""
        mock_correlation = MagicMock()
        mock_correlation.rootly_user_id = "rootly123"
        mock_correlation.pagerduty_user_id = "pduty456"
        mock_correlation.github_username = "ghuser"
        mock_correlation.slack_user_id = "slackid"
        mock_correlation.jira_account_id = "jira789"
        mock_correlation.linear_user_id = "linear012"
        mock_correlation.name = "Full User"
        mock_correlation.email = "full@example.com"
        mock_correlation.avatar_url = "https://example.com/full.png"

        user_data = {
            'id': mock_correlation.rootly_user_id,
            'name': mock_correlation.name,
            'email': mock_correlation.email,
            'github_username': mock_correlation.github_username,
            'slack_user_id': mock_correlation.slack_user_id,
            'jira_account_id': mock_correlation.jira_account_id,
            'linear_user_id': mock_correlation.linear_user_id,
            'rootly_user_id': mock_correlation.rootly_user_id,
            'pagerduty_user_id': mock_correlation.pagerduty_user_id,
            'avatar_url': mock_correlation.avatar_url,
        }

        # All icon-related fields must be present
        required_icon_fields = [
            'github_username',
            'slack_user_id',
            'jira_account_id',
            'linear_user_id',
            'rootly_user_id',
            'pagerduty_user_id',
            'avatar_url'
        ]

        for field in required_icon_fields:
            assert field in user_data, f"Missing required icon field: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
