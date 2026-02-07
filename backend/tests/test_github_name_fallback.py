"""
Tests for name-based GitHub matching fallback in GitHubCollector._correlate_email_to_github().

Verifies that when synced members and manual mappings both fail,
the collector falls back to EnhancedGitHubMatcher.match_name_to_github().
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.github_collector import GitHubCollector


@pytest.fixture
def collector():
    return GitHubCollector()


@pytest.mark.asyncio
async def test_name_fallback_finds_match(collector):
    """Name fallback should return a match when synced/manual lookups fail."""
    with patch.object(collector, '_check_synced_members', new_callable=AsyncMock, return_value=None), \
         patch.object(collector, '_check_manual_mappings', new_callable=AsyncMock, return_value=None), \
         patch('app.services.enhanced_github_matcher.EnhancedGitHubMatcher') as MockMatcher:

        instance = MockMatcher.return_value
        instance.match_name_to_github = AsyncMock(return_value='spencercheng')

        result = await collector._correlate_email_to_github(
            email='spencer@example.com',
            token='ghp_test123',
            user_id=1,
            full_name='Spencer Cheng',
        )

        assert result == 'spencercheng'
        MockMatcher.assert_called_once_with('ghp_test123', collector.organizations)
        instance.match_name_to_github.assert_awaited_once_with('Spencer Cheng', fallback_email='spencer@example.com')


@pytest.mark.asyncio
async def test_name_fallback_skipped_when_no_full_name(collector):
    """Fallback should be skipped when full_name is not provided."""
    with patch.object(collector, '_check_synced_members', new_callable=AsyncMock, return_value=None), \
         patch.object(collector, '_check_manual_mappings', new_callable=AsyncMock, return_value=None), \
         patch('app.services.enhanced_github_matcher.EnhancedGitHubMatcher') as MockMatcher:

        result = await collector._correlate_email_to_github(
            email='spencer@example.com',
            token='ghp_test123',
            user_id=1,
            full_name=None,
        )

        assert result is None
        MockMatcher.assert_not_called()


@pytest.mark.asyncio
async def test_name_fallback_skipped_when_no_token(collector):
    """Fallback (and entire method) should return None when token is missing."""
    result = await collector._correlate_email_to_github(
        email='spencer@example.com',
        token=None,
        user_id=1,
        full_name='Spencer Cheng',
    )

    assert result is None


@pytest.mark.asyncio
async def test_name_fallback_handles_exception_gracefully(collector):
    """If the matcher raises, the method should return None instead of propagating."""
    with patch.object(collector, '_check_synced_members', new_callable=AsyncMock, return_value=None), \
         patch.object(collector, '_check_manual_mappings', new_callable=AsyncMock, return_value=None), \
         patch('app.services.enhanced_github_matcher.EnhancedGitHubMatcher') as MockMatcher:

        instance = MockMatcher.return_value
        instance.match_name_to_github = AsyncMock(side_effect=RuntimeError('API timeout'))

        result = await collector._correlate_email_to_github(
            email='spencer@example.com',
            token='ghp_test123',
            user_id=1,
            full_name='Spencer Cheng',
        )

        assert result is None


@pytest.mark.asyncio
async def test_synced_member_takes_priority_over_name_fallback(collector):
    """When synced members returns a match, name fallback should never run."""
    with patch.object(collector, '_check_synced_members', new_callable=AsyncMock, return_value='spencer-synced'), \
         patch('app.services.enhanced_github_matcher.EnhancedGitHubMatcher') as MockMatcher:

        result = await collector._correlate_email_to_github(
            email='spencer@example.com',
            token='ghp_test123',
            user_id=1,
            full_name='Spencer Cheng',
        )

        assert result == 'spencer-synced'
        MockMatcher.assert_not_called()
