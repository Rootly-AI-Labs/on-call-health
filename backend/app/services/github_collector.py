"""
GitHub data collector for web app burnout analysis.
"""
import logging
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional
import requests
import asyncio
import os
import pytz
from sqlalchemy import or_, and_

logger = logging.getLogger(__name__)


class GitHubCollector:
    """Collects GitHub activity data for burnout analysis."""
    
    def __init__(self):
        self.cache_dir = Path('.github_cache')
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Business hours configuration
        self.business_hours = {'start': 9, 'end': 17}
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests
        
        # GitHub organizations to search
        self.organizations = ["Rootly-AI-Labs", "rootlyhq"]

        # Cache for email mapping
        self._email_mapping_cache = None
        
    async def _correlate_email_to_github(self, email: str, token: str, user_id: Optional[int] = None, full_name: Optional[str] = None) -> Optional[str]:
        """
        Correlate an email address to a GitHub username using multiple strategies.

        This checks in order:
        1. Manual mappings from user_mappings table (highest priority)
        2. Enhanced matching algorithm with multiple strategies
        3. Legacy discovered email mappings from organization members
        """
        if not token:
            logger.debug("No GitHub token provided for correlation")
            return None

        try:
            # FIRST: Check user_correlations table for synced members (from "Sync Members" feature)
            logger.debug(f"🔍 [CORRELATION] Checking user_correlations for {email}")
            synced_username = await self._check_synced_members(email, user_id)
            if synced_username:
                return synced_username

            # SECOND: Check manual mappings from user_mappings table (mapping drawer)
            if user_id:
                logger.debug(f"🔍 [CORRELATION] Checking user_mappings for {email}")
                manual_username = await self._check_manual_mappings(email, user_id)
                if manual_username:
                    return manual_username

            # FALLBACK: Try name-based matching against org members
            if full_name and token:
                try:
                    from .enhanced_github_matcher import EnhancedGitHubMatcher
                    matcher = EnhancedGitHubMatcher(token, self.organizations)
                    name_match = await matcher.match_name_to_github(full_name, fallback_email=email)
                    if name_match:
                        logger.info(f"✅ [NAME_FALLBACK] Matched {email} -> {name_match} via name '{full_name}'")
                        return name_match
                    else:
                        logger.debug(f"[NAME_FALLBACK] No match found for name '{full_name}' ({email})")
                except Exception as e:
                    logger.warning(f"⚠️ [NAME_FALLBACK] Error during name matching for '{full_name}': {e}")

            return None

        except Exception as e:
            logger.error(f"❌ [CORRELATION_ERROR] Error correlating email {email} to GitHub: {e}")
            return None
    
    async def _check_manual_mappings(self, email: str, user_id: int) -> Optional[str]:
        """
        Check user_mappings table for manual GitHub mappings.

        Args:
            email: The email address to look up
            user_id: The user ID who owns the mappings

        Returns:
            GitHub username if found, None otherwise
        """
        try:
            # Validate user_id is an integer (not a PagerDuty/Rootly user ID string)
            if not isinstance(user_id, int):
                logger.warning(f"Invalid user_id type for manual mapping check: {type(user_id).__name__}: {user_id}")
                return None

            # Use SessionLocal to avoid connection pool exhaustion
            from ..models import SessionLocal, UserMapping

            db = SessionLocal()
            try:
                # Query for manual mapping
                user_mapping = db.query(UserMapping).filter(
                    UserMapping.user_id == user_id,
                    UserMapping.source_platform == 'rootly',
                    UserMapping.source_identifier == email,
                    UserMapping.target_platform == 'github',
                    UserMapping.target_identifier.isnot(None),
                    UserMapping.target_identifier != ''
                ).order_by(UserMapping.created_at.desc()).first()

                if user_mapping and user_mapping.target_identifier:
                    username = user_mapping.target_identifier
                    logger.info(f"Found manual GitHub mapping: {email} -> {username}")
                    return username
                else:
                    logger.debug(f"No manual GitHub mapping found for {email}")
                    return None
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error checking manual mappings: {e}")
            return None

    async def _check_synced_members(self, email: str, user_id: int) -> Optional[str]:
        """
        Check user_correlations table for synced GitHub usernames (from Sync Members feature).

        Args:
            email: The email address to look up
            user_id: The user ID who owns the correlations

        Returns:
            GitHub username if found, None otherwise
        """
        try:
            # Convert user_id to int if it's a string
            if isinstance(user_id, str):
                try:
                    user_id = int(user_id)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ [SYNCED_CHECK] Invalid user_id type: {type(user_id).__name__}: {user_id}")
                    return None
            elif not isinstance(user_id, int):
                logger.warning(f"⚠️ [SYNCED_CHECK] Invalid user_id type: {type(user_id).__name__}: {user_id}")
                return None

            logger.debug(f"🔍 [SYNCED_CHECK] Querying user_correlations for email: {email}")

            # Use SessionLocal instead of creating new engine/connection for each query
            # This prevents "too many clients" error when processing large teams
            from ..models import SessionLocal, UserCorrelation, User

            db = SessionLocal()
            try:
                # Get user's organization_id for filtering
                org_id = None
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    org_id = user.organization_id
                    logger.debug(f"🔍 [SYNCED_CHECK] User {user_id} belongs to organization {org_id}")

                # Query for synced member with organization filter to prevent cross-org data leakage
                if org_id:
                    user_correlation = db.query(UserCorrelation).filter(
                        UserCorrelation.email == email,
                        UserCorrelation.github_username.isnot(None),
                        UserCorrelation.github_username != '',
                        or_(
                            UserCorrelation.user_id == user_id,  # Personal mappings
                            and_(
                                UserCorrelation.user_id.is_(None),
                                UserCorrelation.organization_id == org_id
                            )  # Team roster mappings
                        )
                    ).first()
                else:
                    # Fallback: no organization filter if org_id not found (backward compatibility)
                    logger.warning(f"⚠️ [SYNCED_CHECK] No organization_id found for user {user_id}, using unfiltered query")
                    user_correlation = db.query(UserCorrelation).filter(
                        UserCorrelation.email == email,
                        UserCorrelation.github_username.isnot(None),
                        UserCorrelation.github_username != ''
                    ).first()

                if user_correlation and user_correlation.github_username:
                    return user_correlation.github_username
                return None
            finally:
                db.close()

        except Exception as e:
            logger.error(f"❌ [SYNCED_CHECK_ERROR] Error checking synced members for {email}: {type(e).__name__}: {e}")
            return None

    async def _build_email_mapping(self, token: str) -> Dict[str, str]:
        """
        Build mapping of email addresses to GitHub usernames by discovering org members
        and mining their commits. Mimics the original burnout detector logic.
        """
        email_to_username = {}
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Rootly-Burnout-Detector'
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Get all GitHub users from organizations
                github_users = set()
                
                for org in self.organizations:
                    try:
                        # Get organization members
                        members_url = f"https://api.github.com/orgs/{org}/members"
                        async with session.get(members_url, headers=headers) as resp:
                            if resp.status == 200:
                                members_data = await resp.json()
                                org_members = [member['login'] for member in members_data]
                                github_users.update(org_members)
                                logger.info(f"Found {len(org_members)} members in {org}")
                            else:
                                logger.warning(f"Failed to get members for {org}: {resp.status}")
                    except Exception as e:
                        logger.error(f"Error getting members for org {org}: {e}")
                
                logger.info(f"Total GitHub users to process: {len(github_users)}")
                
                # For each user, try to discover their email from recent commits
                for username in list(github_users):  # Process all users
                    try:
                        emails = await self._get_user_emails(username, session, headers)
                        for email in emails:
                            email_lower = email.lower()
                            if email_lower not in email_to_username:
                                email_to_username[email_lower] = username
                                logger.debug(f"Mapped {email_lower} -> {username}")
                    except Exception as e:
                        logger.error(f"Error getting emails for user {username}: {e}")
                
                logger.info(f"Built email mapping with {len(email_to_username)} entries")
                return email_to_username
                
        except Exception as e:
            logger.error(f"Error building email mapping: {e}")
            return {}
    
    async def _get_user_emails(self, username: str, session, headers) -> set:
        """Get email addresses used by a GitHub user in recent commits."""
        emails = set()
        
        try:
            # Get user's public profile email first
            user_url = f"https://api.github.com/users/{username}"
            async with session.get(user_url, headers=headers) as resp:
                if resp.status == 200:
                    user_data = await resp.json()
                    if user_data.get('email'):
                        emails.add(user_data['email'])
            
            # Get user's recent events to find repositories they've contributed to
            # Reduced from 100 to 30 to minimize API calls
            events_url = f"https://api.github.com/users/{username}/events?per_page=30"
            async with session.get(events_url, headers=headers) as resp:
                if resp.status == 200:
                    events_data = await resp.json()
                    
                    # Look for Push events to find repositories
                    repos_to_check = set()
                    for event in events_data:  # Check all events
                        if event.get('type') == 'PushEvent' and event.get('repo'):
                            repo_name = event['repo']['name']
                            repos_to_check.add(repo_name)
                    
                    # For each repo, check recent commits by this user
                    # Limit to 3 repos to reduce API calls
                    for repo_name in list(repos_to_check)[:3]:
                        try:
                            # Reduced from 100 to 10 commits per repo
                            commits_url = f"https://api.github.com/repos/{repo_name}/commits?author={username}&per_page=10"
                            async with session.get(commits_url, headers=headers) as resp:
                                if resp.status == 200:
                                    commits_data = await resp.json()
                                    for commit in commits_data:
                                        if commit.get('commit', {}).get('author', {}).get('email'):
                                            email = commit['commit']['author']['email']
                                            emails.add(email)
                        except Exception as e:
                            logger.debug(f"Error checking commits for {repo_name}: {e}")
        
        except Exception as e:
            logger.error(f"Error getting emails for {username}: {e}")
        
        return emails
        
    async def _fetch_real_github_data(self, username: str, email: str, start_date: datetime, end_date: datetime, token: str, timezone: str = 'UTC') -> Dict:
        """Fetch real GitHub data using the GitHub API with enterprise resilience."""

        logger.debug(f"🔍 [GITHUB_API] Starting data fetch for {username} ({email}): {start_date.date()} to {end_date.date()}")

        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.cloak-preview+json',  # Required for commit search API
            'User-Agent': 'Rootly-Burnout-Detector'
        }

        since_iso = start_date.isoformat()
        until_iso = end_date.isoformat()

        # Fetch user info
        user_url = f"https://api.github.com/users/{username}"

        try:
            # Phase 2.3: Use API manager for resilient GitHub API calls
            from .github_api_manager import github_api_manager, GitHubPermissionError

            # Use search API to get counts only (1 call instead of paginating)
            # Build org filters to search within configured organizations
            org_filters = "+".join([f"org:{org}" for org in self.organizations])

            # TEMPORARY DEBUG: Remove org filters to test if they're blocking results
            # Get commits across all repos in configured orgs
            commits_url = f"https://api.github.com/search/commits?q=author:{username}+author-date:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}&per_page=1"

            # Get pull requests count
            prs_url = f"https://api.github.com/search/issues?q=author:{username}+type:pr+created:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}&per_page=1"

            logger.debug(f"🔍 [GITHUB_API_URL] Commits query: {commits_url}")
            logger.debug(f"🔍 [GITHUB_API_URL] PRs query: {prs_url}")

            # Make resilient API calls with rate limiting and circuit breaker
            async def fetch_commits():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(commits_url, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status == 401:
                            raise aiohttp.ClientError(f"GitHub API authentication failed (401) - token may be expired or invalid")
                        elif resp.status == 403:
                            raise GitHubPermissionError(f"GitHub API forbidden (403) - token needs 'repo' permission for private repos")
                        else:
                            raise aiohttp.ClientError(f"GitHub API error for commits: {resp.status}")

            async def fetch_prs():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(prs_url, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status == 401:
                            raise aiohttp.ClientError(f"GitHub API authentication failed (401) - token may be expired or invalid")
                        elif resp.status == 403:
                            raise GitHubPermissionError(f"GitHub API forbidden (403) - token needs 'repo' permission for private repos")
                        else:
                            raise aiohttp.ClientError(f"GitHub API error for PRs: {resp.status}")
            
            # Execute with enterprise resilience patterns
            logger.debug(f"🌐 [GITHUB_API] Fetching commits for {username}")
            commits_data = await github_api_manager.safe_api_call(fetch_commits, max_retries=3)
            total_commits = commits_data.get('total_count', 0) if commits_data else 0
            logger.debug(f"📊 [GITHUB_API_RESPONSE] {username} commits response: total_count={total_commits}, incomplete_results={commits_data.get('incomplete_results', 'N/A') if commits_data else 'N/A'}")

            logger.debug(f"🌐 [GITHUB_API] Fetching PRs for {username}")
            prs_data = await github_api_manager.safe_api_call(fetch_prs, max_retries=3)
            total_prs = prs_data.get('total_count', 0) if prs_data else 0
            logger.debug(f"📊 [GITHUB_API_RESPONSE] {username} PRs response: total_count={total_prs}, incomplete_results={prs_data.get('incomplete_results', 'N/A') if prs_data else 'N/A'}")

            logger.debug(f"✅ [GITHUB_API_SUCCESS] {username} ({email}): {total_commits} commits, {total_prs} PRs")

            # Fetch detailed daily commit data with timestamps
            logger.debug(f"🔄 Fetching detailed daily commit data for {username}")
            daily_commits_data = await self.fetch_daily_commit_data(username, start_date, end_date, token, timezone)

            # Build commits array from daily data for timeline processing
            commits_array = []
            after_hours_commits = 0
            weekend_commits = 0
            if daily_commits_data:
                for daily in daily_commits_data:
                    # Create a timestamp for aggregation at midnight of that date
                    date_str = daily.get('date', '')
                    if date_str:
                        # Create timestamps for all commits on this day
                        date_obj = datetime.fromisoformat(date_str)
                        after_hours_count = daily.get('after_hours_commits', 0)
                        weekend_count = daily.get('weekend_commits', 0)  # Tracked for metrics, not separate timestamps
                        total_today = daily.get('total_commits', 0)

                        # Calculate business-hours commits (all commits that are NOT after-hours)
                        business_hours_count = max(0, total_today - after_hours_count)

                        # IMPORTANT: Generate timestamps for BOTH after-hours and business-hours commits
                        # Note: weekend_commits are a subset of after_hours_count or business_hours_count
                        # (a weekend commit is counted in after_hours if at night, or business_hours if during day)
                        # We do NOT generate separate weekend timestamps to avoid double-counting

                        # Generate timestamps for after-hours commits (22:00-23:59 or 00:00-08:59)
                        for i in range(after_hours_count):
                            hour = 22 + (i % 2)  # Alternate between 22 and 23
                            minute = (i * 17) % 60  # Distribute by minute
                            commit_dt = date_obj.replace(hour=hour, minute=minute).isoformat() + 'Z'
                            commits_array.append({"timestamp": commit_dt})

                        # Generate timestamps for business-hours commits (09:00-16:59)
                        for i in range(business_hours_count):
                            hour = 9 + (i % 8)  # Distribute across 8 business hours (9-16)
                            minute = (i * 13) % 60  # Different distribution than after-hours
                            commit_dt = date_obj.replace(hour=hour, minute=minute).isoformat() + 'Z'
                            commits_array.append({"timestamp": commit_dt})

                        after_hours_commits += after_hours_count
                        weekend_commits += weekend_count

            # If we couldn't fetch detailed commit data, report zeros rather than guessing
            if not daily_commits_data:
                after_hours_commits = 0
                weekend_commits = 0

            total_reviews = int(total_prs * 1.5)             # Estimate 1.5 reviews per PR

            days_analyzed = (end_date - start_date).days
            weeks = days_analyzed / 7

            # Calculate percentages
            after_hours_percentage = (after_hours_commits / total_commits) if total_commits > 0 else 0
            weekend_percentage = (weekend_commits / total_commits) if total_commits > 0 else 0

            # Generate burnout indicators
            commits_per_week = total_commits / weeks if weeks > 0 else 0
            burnout_indicators = {
                "excessive_commits": commits_per_week > 15,
                "late_night_activity": after_hours_percentage > 0.25,
                "weekend_work": weekend_percentage > 0.15,
                "large_prs": total_prs > 0 and (total_commits / max(total_prs, 1)) > 10
            }

            return {
                'username': username,
                'email': email,
                'analysis_period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days_analyzed
                },
                'metrics': {
                    'total_commits': total_commits,
                    'total_pull_requests': total_prs,
                    'total_reviews': total_reviews,
                    'commits_per_week': round(commits_per_week, 2),
                    'prs_per_week': round(total_prs / weeks if weeks > 0 else 0, 2),
                    'after_hours_commit_percentage': round(after_hours_percentage, 3),
                    'weekend_commit_percentage': round(weekend_percentage, 3),
                    'repositories_touched': 3,  # Estimate
                    'avg_pr_size': int(total_commits / max(total_prs, 1)) if total_prs > 0 else 50,
                    'clustered_commits': 0  # Would need more detailed analysis
                },
                'burnout_indicators': burnout_indicators,
                'activity_data': {
                    'commits_count': total_commits,
                    'pull_requests_count': total_prs,
                    'reviews_count': total_reviews,
                    'after_hours_commits': after_hours_commits,
                    'weekend_commits': weekend_commits,
                    'avg_pr_size': int(total_commits / max(total_prs, 1)) if total_prs > 0 else 50,
                    'burnout_indicators': burnout_indicators
                },
                'commits': commits_array
            }
            
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            logger.error(f"❌ [GITHUB_API_ERROR] {username} ({email}): {error_type}: {error_msg}")

            # Log additional context for specific error types
            if "401" in error_msg or "authentication" in error_msg.lower():
                logger.error(f"🔐 [GITHUB_API_ERROR] Authentication failed for {username} - token may be expired or invalid")
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                logger.error(f"🚫 [GITHUB_API_ERROR] Permission denied for {username} - token may lack 'repo' scope")
            elif "rate limit" in error_msg.lower():
                logger.error(f"⏱️ [GITHUB_API_ERROR] Rate limit exceeded for {username}")
            elif "timeout" in error_msg.lower():
                logger.error(f"⏰ [GITHUB_API_ERROR] Timeout fetching data for {username}")

            # Don't fall back to mock data - return None to indicate failure
            return None
        
    async def fetch_daily_commit_data(self, username: str, start_date: datetime, end_date: datetime, github_token: str, timezone: str = 'UTC') -> Optional[List[Dict]]:
        """
        Fetch daily commit data for a GitHub user over a specified period.

        Args:
            username: GitHub username
            start_date: Start date for the analysis period
            end_date: End date for the analysis period
            github_token: GitHub API token
            timezone: User's timezone for business hours calculation (default: 'UTC')
            
        Returns:
            List of daily commit data or None if error
        """
        headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Rootly-Burnout-Detector'
        }
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                # Check rate limit before starting
                rate_check_url = "https://api.github.com/rate_limit"
                async with session.get(rate_check_url, headers=headers) as resp:
                    if resp.status == 200:
                        rate_data = await resp.json()
                        remaining = rate_data['rate']['remaining']
                        reset_time = rate_data['rate']['reset']
                        logger.debug(f"GITHUB API: Rate limit remaining: {remaining}, resets at {datetime.fromtimestamp(reset_time)}")

                        if remaining < 100:
                            logger.warning(f"GITHUB API: ⚠️ Rate limit low! Remaining: {remaining}, Reset: {reset_time}")
                        if remaining < 10:
                            logger.error(f"GITHUB API: 🚫 Critical rate limit ({remaining} remaining)! Aborting.")
                            return None
                
                # Initialize daily data structure
                daily_commits = {}
                current_date = start_date
                
                while current_date <= end_date:
                    date_str = current_date.strftime('%Y-%m-%d')
                    daily_commits[date_str] = {
                        'date': date_str,
                        'total_commits': 0,  # Total commits for this day
                        'after_hours_commits': 0,  # Commits during after-hours (22:00-08:59)
                        'weekend_commits': 0  # Commits on weekends
                    }
                    current_date += timedelta(days=1)
                
                # Fetch commits using search API
                search_url = f"https://api.github.com/search/commits"
                # TEMPORARY DEBUG: Remove org filters to test if they're blocking results
                # Build org filters to search within configured organizations
                # org_filters = "+".join([f"org:{org}" for org in self.organizations])
                query = f"author:{username} author-date:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
                
                page = 1
                per_page = 100
                total_fetched = 0
                
                while True:
                    params = {
                        'q': query,
                        'sort': 'author-date',
                        'order': 'asc',
                        'page': page,
                        'per_page': per_page
                    }
                    
                    async with session.get(search_url, headers=headers, params=params) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get('items', [])
                            
                            if not items:
                                break
                                
                            # Process each commit
                            for commit_item in items:
                                commit = commit_item.get('commit', {})
                                author = commit.get('author', {})
                                date_str = author.get('date', '')
                                
                                if date_str:
                                    # Parse commit datetime (UTC)
                                    commit_dt_utc = datetime.fromisoformat(date_str.replace('Z', '+00:00'))

                                    # Convert to user's local timezone for business hours calculation
                                    try:
                                        tz = pytz.timezone(timezone)
                                        commit_dt_local = commit_dt_utc.astimezone(tz)
                                    except (pytz.exceptions.UnknownTimeZoneError, Exception):
                                        logger.warning(f"Invalid timezone '{timezone}', using UTC")
                                        commit_dt_local = commit_dt_utc

                                    commit_date = commit_dt_utc.strftime('%Y-%m-%d')

                                    if commit_date in daily_commits:
                                        daily_commits[commit_date]['total_commits'] += 1

                                        # Check if after hours (using configurable business hours in local timezone)
                                        hour = commit_dt_local.hour
                                        if hour < self.business_hours['start'] or hour >= self.business_hours['end']:
                                            daily_commits[commit_date]['after_hours_commits'] += 1

                                        # Check if weekend (using local timezone date)
                                        if commit_dt_local.weekday() >= 5:  # Saturday = 5, Sunday = 6
                                            daily_commits[commit_date]['weekend_commits'] += 1
                            
                            total_fetched += len(items)
                            
                            # Check if we've fetched all results
                            if total_fetched >= data.get('total_count', 0):
                                break
                                
                            page += 1
                            
                            # GitHub search API has a limit of 1000 results
                            if total_fetched >= 1000:
                                logger.warning(f"Reached GitHub search API limit of 1000 results for {username}")
                                break
                                
                        elif resp.status == 401:
                            logger.error(f"GITHUB API: 🔐 Authentication failed for user {username} - token may be expired or invalid")
                            return None
                        elif resp.status == 403:
                            rate_remaining = resp.headers.get('X-RateLimit-Remaining', 'unknown')
                            rate_reset = resp.headers.get('X-RateLimit-Reset', 'unknown')
                            logger.error(f"GITHUB API: 🚫 RATE LIMITED (403)! Remaining: {rate_remaining}, Reset: {rate_reset}")
                            return None
                        elif resp.status == 429:
                            retry_after = resp.headers.get('Retry-After', 'unknown')
                            logger.error(f"GITHUB API: 🚫 RATE LIMITED (429)! Retry-After: {retry_after}s")
                            return None
                        else:
                            logger.error(f"GITHUB API: Request failed with status {resp.status}")
                            return None
                
                # Convert to list sorted by date
                daily_data = sorted(daily_commits.values(), key=lambda x: x['date'])
                
                logger.debug(f"Fetched {total_fetched} commits for {username} from {start_date} to {end_date}")
                return daily_data
                
        except Exception as e:
            logger.error(f"Error fetching daily commit data for {username}: {e}")
            return None
    
    async def collect_github_data_for_user(self, user_email: str, days: int = 30, github_token: str = None, user_id: Optional[int] = None, full_name: Optional[str] = None, timezone: str = 'UTC') -> Optional[Dict]:
        """
        Collect GitHub activity data for a single user using email correlation.

        Args:
            user_email: User's email to correlate with GitHub
            days: Number of days to analyze
            github_token: GitHub API token for authentication
            user_id: User ID for checking manual mappings
            full_name: User's full name
            timezone: User's timezone for business hours calculation (default: 'UTC')

        Returns:
            GitHub activity data or None if no correlation found
        """
        # Use email-based correlation to find GitHub username
        github_username = await self._correlate_email_to_github(user_email, github_token, user_id, full_name)

        if not github_username:
            return None

        # Set up date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Use real GitHub API if token provided
        if github_token:
            result = await self._fetch_real_github_data(github_username, user_email, start_date, end_date, github_token, timezone)
            if not result:
                logger.error(f"Failed to fetch GitHub data for {github_username}")
                return None
            return result
        else:
            logger.warning(f"No GitHub token provided, generating mock data for {github_username}")
            return self._generate_mock_github_data(github_username, user_email, start_date, end_date)
    
    def _generate_mock_github_data(self, username: str, email: str, start_date: datetime, end_date: datetime) -> Dict:
        """Generate realistic mock GitHub data for testing."""

        # Generate some realistic activity
        days_analyzed = (end_date - start_date).days

        # Base activity levels (some users more active than others)
        activity_multiplier = random.choice([0.5, 0.8, 1.0, 1.2, 1.5])

        # Generate commits
        total_commits = int(random.randint(10, 50) * activity_multiplier)
        after_hours_commits = int(total_commits * random.uniform(0.1, 0.3))
        weekend_commits = int(total_commits * random.uniform(0.05, 0.2))

        # Generate PRs
        total_prs = int(random.randint(2, 15) * activity_multiplier)

        # Generate reviews
        total_reviews = int(random.randint(5, 25) * activity_multiplier)

        # Calculate weekly averages
        weeks = days_analyzed / 7
        commits_per_week = total_commits / weeks if weeks > 0 else 0
        prs_per_week = total_prs / weeks if weeks > 0 else 0

        # Calculate percentages
        after_hours_percentage = (after_hours_commits / total_commits) if total_commits > 0 else 0
        weekend_percentage = (weekend_commits / total_commits) if total_commits > 0 else 0

        # Generate burnout indicators
        burnout_indicators = {
            "excessive_commits": commits_per_week > 15,
            "late_night_activity": after_hours_percentage > 0.25,
            "weekend_work": weekend_percentage > 0.15,
            "large_prs": random.choice([True, False])  # Simplified
        }

        # Generate mock commit objects with timestamps
        commits_array = []
        current_date = start_date
        remaining_after_hours = after_hours_commits
        while current_date <= end_date and remaining_after_hours > 0:
            # Add some after-hours commits to this day
            commits_today = random.randint(1, min(3, remaining_after_hours))
            for i in range(commits_today):
                hour = 22 + (i % 2)  # Alternate between 22 and 23
                minute = (i * 17) % 60
                commit_dt = current_date.replace(hour=hour, minute=minute).isoformat() + 'Z'
                commits_array.append({"timestamp": commit_dt})
                remaining_after_hours -= 1
            current_date += timedelta(days=1)

        return {
            'username': username,
            'email': email,
            'analysis_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': days_analyzed
            },
            'metrics': {
                'total_commits': total_commits,
                'total_pull_requests': total_prs,
                'total_reviews': total_reviews,
                'commits_per_week': round(commits_per_week, 2),
                'prs_per_week': round(prs_per_week, 2),
                'after_hours_commit_percentage': round(after_hours_percentage, 3),
                'weekend_commit_percentage': round(weekend_percentage, 3),
                'repositories_touched': random.randint(2, 8),
                'avg_pr_size': random.randint(50, 300),
                'clustered_commits': random.randint(0, 5)
            },
            'burnout_indicators': burnout_indicators,
            'activity_data': {
                'commits_count': total_commits,
                'pull_requests_count': total_prs,
                'reviews_count': total_reviews,
                'commits_per_week': round(commits_per_week, 2),
                'after_hours_commits': after_hours_commits,
                'weekend_commits': weekend_commits,
                'avg_pr_size': random.randint(50, 300),
                'burnout_indicators': burnout_indicators
            },
            'commits': commits_array
        }
    
    def _is_business_hours(self, dt: datetime) -> bool:
        """Check if datetime is within business hours."""
        return (
            dt.weekday() < 5 and  # Monday = 0, Friday = 4
            self.business_hours['start'] <= dt.hour < self.business_hours['end']
        )
    
    def _rate_limit(self):
        """Simple rate limiting to avoid hitting GitHub API limits."""
        import time
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        
        self.last_request_time = time.time()


async def collect_team_github_data(team_emails: List[str], days: int = 30, github_token: str = None, user_id: Optional[int] = None, timezone: str = 'UTC', email_to_name: Optional[Dict[str, str]] = None) -> Dict[str, Dict]:
    """
    Collect GitHub data for all team members.

    Args:
        team_emails: List of team member emails
        days: Number of days to analyze
        github_token: GitHub API token for real data collection
        user_id: User ID for checking manual mappings
        timezone: Fallback timezone if per-user timezone not found (default: 'UTC')
        email_to_name: Optional mapping of email -> full name for name-based matching

    Returns:
        Dict mapping email -> github_activity_data
    """
    collector = GitHubCollector()
    github_data = {}

    # Get organization_id for filtering user_correlations
    organization_id = None
    if user_id is not None:
        try:
            from ..models import SessionLocal, User
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    organization_id = user.organization_id
                    logger.debug(f"User {user_id} belongs to organization {organization_id}")
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"Could not retrieve organization_id: {e}")

    # Open single database connection for all timezone lookups (performance optimization)
    db_session = None
    if user_id is not None:
        try:
            from ..models import SessionLocal, UserCorrelation
            from sqlalchemy import desc
            db_session = SessionLocal()
        except Exception as e:
            logger.warning(f"⚠️ Could not create database session for timezone lookups: {e}")

    try:
        for email in team_emails:
            try:
                full_name = email_to_name.get(email) if email_to_name else None

                # Get user-specific timezone from UserCorrelation if available
                user_timezone = timezone  # Use parameter as fallback
                if db_session is not None:
                    try:
                        # Filter by organization_id to avoid cross-org contamination
                        filters = [
                            UserCorrelation.email == email,
                            UserCorrelation.user_id.is_(None)  # Team roster only
                        ]
                        if organization_id:
                            filters.append(UserCorrelation.organization_id == organization_id)

                        user_correlation = db_session.query(UserCorrelation).filter(*filters).order_by(
                            UserCorrelation.github_username.isnot(None).desc(),  # Prefer records with username
                            desc(UserCorrelation.id)  # Most recent first
                        ).first()
                        if user_correlation and user_correlation.timezone:
                            user_timezone = user_correlation.timezone
                            logger.debug(f"Using timezone {user_timezone} for {email}")
                    except Exception as tz_error:
                        logger.warning(f"⚠️ Timezone retrieval failed for {email}, defaulting to {timezone}: {tz_error}")

                user_data = await collector.collect_github_data_for_user(email, days, github_token, user_id, full_name=full_name, timezone=user_timezone)
                if user_data:
                    github_data[email] = user_data
            except Exception as e:
                logger.error(f"Failed to collect GitHub data for {email}: {e}")
    finally:
        # Close database connection after all timezone lookups complete
        if db_session is not None:
            db_session.close()

    logger.info(f"Collected GitHub data for {len(github_data)} users out of {len(team_emails)}")
    return github_data