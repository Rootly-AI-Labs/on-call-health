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

        # Track when GitHub search rate limit is hit so we can abort remaining users
        self._rate_limited = False
        self._rate_limit_reset = None  # Unix timestamp string from X-RateLimit-Reset header

        # GitHub organizations - fetched dynamically based on token access
        self._organizations_cache = {}  # Cache: token_hash -> [org_list, timestamp]
        self._org_cache_ttl = 3600  # Cache orgs for 1 hour
        self._org_cache_locks = {}  # Lock per token to prevent concurrent API calls

        # Cache for email mapping
        self._email_mapping_cache = None

    async def get_accessible_orgs(self, token: str) -> Optional[List[str]]:
        """
        Fetch organizations the token has access to from GitHub API.
        Caches results for 1 hour to avoid repeated API calls.

        Returns:
            List[str]: List of organization names (empty list if user has no orgs)
            None: If API call failed or token is invalid
        """
        # Input validation
        if not token or not isinstance(token, str) or len(token.strip()) == 0:
            logger.warning("Invalid GitHub token provided")
            return None

        # Create cache key (full SHA256 hash to prevent collisions)
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Check cache (fast path, no lock needed)
        now = datetime.now().timestamp()
        if token_hash in self._organizations_cache:
            orgs, cached_time = self._organizations_cache[token_hash]
            if now - cached_time < self._org_cache_ttl:
                logger.debug(f"Using cached organizations ({len(orgs)} orgs)")
                return orgs

        # Acquire lock for this token to prevent concurrent API calls
        if token_hash not in self._org_cache_locks:
            self._org_cache_locks[token_hash] = asyncio.Lock()

        async with self._org_cache_locks[token_hash]:
            # Double-check cache after acquiring lock (another request might have populated it)
            if token_hash in self._organizations_cache:
                orgs, cached_time = self._organizations_cache[token_hash]
                if now - cached_time < self._org_cache_ttl:
                    logger.debug(f"Using cached organizations ({len(orgs)} orgs)")
                    return orgs

            # Fetch from GitHub API
            try:
                import aiohttp
                headers = {
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Rootly-Burnout-Detector'
                }

                # Configure timeout and SSL validation
                # Use shorter timeout (5s) to avoid blocking other operations
                timeout = aiohttp.ClientTimeout(total=5)
                connector = aiohttp.TCPConnector(ssl=True)

                async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                    async with session.get("https://api.github.com/user/orgs", headers=headers) as resp:
                        if resp.status == 200:
                            orgs_data = await resp.json()
                            org_names = [org.get("login") for org in orgs_data if org.get("login")]

                            # Cache the result (including empty lists)
                            self._organizations_cache[token_hash] = (org_names, now)

                            # Log count only (don't expose org names in logs)
                            logger.info(f"✅ Token has access to {len(org_names)} organizations")
                            return org_names
                        elif resp.status == 401:
                            logger.error("GitHub token is invalid or expired")
                            return None
                        elif resp.status == 403:
                            logger.warning("GitHub token needs 'read:org' scope to list organizations")
                            return None
                        else:
                            logger.warning(f"Failed to fetch orgs (status {resp.status})")
                            return None
            except aiohttp.ClientError as e:
                logger.error(f"GitHub API client error: {type(e).__name__}")
                return None
            except asyncio.TimeoutError:
                logger.error("GitHub API request timed out after 5s")
                return None
            except Exception as e:
                # Sanitized logging to prevent token leakage in error messages
                logger.error(f"Unexpected error fetching GitHub organizations: {type(e).__name__}", exc_info=False)
                return None

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

            # NO FALLBACK - If not synced, return None
            # Users must sync members in the Management page to get GitHub data
            logger.info(f"⚠️ [NO_MAPPING] No GitHub mapping found for {email}. User must sync members in Management page.")
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
            # Convert user_id to int if it's not already
            if not isinstance(user_id, int):
                try:
                    user_id = int(user_id)
                except (ValueError, TypeError):
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
                # Get organizations the token has access to
                accessible_orgs = await self.get_accessible_orgs(token)
                if accessible_orgs is None:
                    logger.warning("Failed to fetch orgs - cannot build email mapping")
                    return {}
                if not accessible_orgs:
                    logger.info("User has no organization memberships - cannot build email mapping")
                    return {}

                # Get all GitHub users from organizations
                github_users = set()

                for org in accessible_orgs:
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
            from .github_api_manager import github_api_manager, GitHubPermissionError, GitHubRateLimitError

            # Get organizations the token has access to (cached after first user)
            accessible_orgs = await self.get_accessible_orgs(token)

            # Build org filters based on token's access
            if accessible_orgs:  # Non-empty list
                org_filters = "+".join([f"org:{org}" for org in accessible_orgs])
                org_filter_query = f"+{org_filters}"
                logger.debug(f"🔍 Using org filters for {len(accessible_orgs)} organizations")
            elif accessible_orgs is not None:  # Empty list but API succeeded
                logger.info(f"User has no organization memberships - searching all repos for {username}")
                org_filter_query = ""
            else:  # API failed (returned None)
                logger.warning(f"⚠️ Could not determine accessible orgs - searching all repos for {username}")
                org_filter_query = ""

            # Step 1 & 2: Fetch daily commit data + PR count via GraphQL.
            # GraphQL uses 5,000 points/hour vs Search API's 30 requests/minute — same token works.
            logger.debug(f"🔄 [GRAPHQL] Fetching daily commit data for {username}")
            daily_commits_data, total_commits, total_prs, real_timestamps, repos_count = await self.fetch_daily_commit_data_graphql(
                username, email, start_date, end_date, token, timezone
            )

            logger.debug(f"✅ [GITHUB_API_SUCCESS] {username} ({email}): {total_commits} commits, {total_prs} PRs")

            # Build commits array from real timestamps fetched via GraphQL
            commits_array = [{"timestamp": ts} for ts in real_timestamps]

            # Sum after-hours and weekend counts from daily classification
            after_hours_commits = sum(d.get('after_hours_commits', 0) for d in daily_commits_data) if daily_commits_data else 0
            weekend_commits = sum(d.get('weekend_commits', 0) for d in daily_commits_data) if daily_commits_data else 0

            total_reviews = 0  # Not fetched from GitHub

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
                    'repositories_touched': repos_count,
                    'avg_pr_size': 0,
                    'clustered_commits': 0
                },
                'burnout_indicators': burnout_indicators,
                'activity_data': {
                    'commits_count': total_commits,
                    'pull_requests_count': total_prs,
                    'reviews_count': total_reviews,
                    'after_hours_commits': after_hours_commits,
                    'weekend_commits': weekend_commits,
                    'commits_per_week': round(commits_per_week, 2),
                    'avg_pr_size': 0,  # PR size in lines not available from GitHub Search API
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

                # Get organizations the token has access to (cached)
                accessible_orgs = await self.get_accessible_orgs(github_token)

                # Build org filters based on token's access
                if accessible_orgs:  # Non-empty list
                    org_filters = " ".join([f"org:{org}" for org in accessible_orgs])
                    query = f"author:{username} author-date:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')} {org_filters}"
                elif accessible_orgs is not None:  # Empty list but API succeeded
                    logger.info(f"User has no organization memberships - searching all repos for {username}")
                    query = f"author:{username} author-date:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
                else:  # API failed (returned None)
                    logger.warning(f"Could not determine accessible orgs - searching all repos for {username}")
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
                            rate_remaining = resp.headers.get('X-RateLimit-Remaining', '1')
                            rate_reset = resp.headers.get('X-RateLimit-Reset', 'unknown')
                            if rate_remaining == '0':
                                self._rate_limited = True
                                self._rate_limit_reset = rate_reset
                                logger.error(f"GITHUB API: 🚫 SEARCH RATE LIMITED (403)! Remaining: {rate_remaining}, Reset: {rate_reset}. Aborting remaining users.")
                            else:
                                logger.warning(f"GITHUB API: 🚫 FORBIDDEN (403) - likely insufficient token permissions")
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

    # ─────────────────────────────────────────────────────────────────────────
    # GraphQL methods — use 5,000 points/hour vs Search API's 30 requests/min
    # Same Personal Access Token (ghp_) works — no token change needed.
    # ─────────────────────────────────────────────────────────────────────────

    async def _graphql_query(self, query: str, variables: dict, token: str) -> Optional[dict]:
        """
        Execute a GitHub GraphQL query.
        Uses a separate rate limit bucket (5,000 points/hour) vs REST Search API (30/min).
        """
        import aiohttp
        url = "https://api.github.com/graphql"
        headers = {
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Rootly-Burnout-Detector"
        }
        payload = {"query": query, "variables": variables}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()

                        # Read rate limit from response HEADERS (always present, unlike extensions)
                        from datetime import timezone as _tz
                        remaining = int(resp.headers.get('X-RateLimit-Remaining', 5000))
                        limit = int(resp.headers.get('X-RateLimit-Limit', 5000))
                        reset_ts = resp.headers.get('X-RateLimit-Reset')

                        try:
                            if reset_ts:
                                reset_dt = datetime.fromtimestamp(int(reset_ts), tz=_tz.utc)
                                now_utc = datetime.now(_tz.utc)
                                mins_left = max(0, int((reset_dt - now_utc).total_seconds() / 60))
                                reset_str = reset_dt.strftime('%H:%M:%S UTC')
                                logger.info(
                                    f"📊 [GRAPHQL_RATE] Remaining: {remaining}/{limit} pts | "
                                    f"Resets at: {reset_str} (in {mins_left}m)"
                                )
                            else:
                                logger.info(f"📊 [GRAPHQL_RATE] Remaining: {remaining}/{limit} pts")
                        except Exception:
                            logger.info(f"📊 [GRAPHQL_RATE] Remaining: {remaining}/{limit} pts")

                        # Flag rate limited if running low
                        if remaining < 300:
                            self._rate_limited = True
                            self._rate_limit_reset = reset_ts
                            logger.warning(f"⚠️ [GRAPHQL_RATE_LIMIT] Only {remaining} points remaining — flagging rate limited")

                        if "errors" in result:
                            logger.warning(f"⚠️ [GRAPHQL_ERRORS] {result['errors']}")

                        return result.get("data")

                    elif resp.status == 401:
                        logger.error("GitHub GraphQL: 🔐 Authentication failed (401) — token may be expired")
                        return None
                    elif resp.status == 403:
                        self._rate_limited = True
                        logger.error("GitHub GraphQL: 🚫 RATE LIMITED (403)")
                        return None
                    elif resp.status == 502:
                        logger.warning("GitHub GraphQL: 502 Bad Gateway — skipping")
                        return None
                    else:
                        logger.warning(f"GitHub GraphQL: Unexpected status {resp.status}")
                        return None

        except Exception as e:
            logger.error(f"GitHub GraphQL request failed: {type(e).__name__}: {e}")
            return None

    async def _fetch_contributions_summary(self, username: str, start_date: datetime, end_date: datetime, token: str) -> Optional[dict]:
        """
        Fetch contribution summary for a GitHub user using GraphQL.
        Returns total commits, total PRs, daily counts, and top repos.
        Cost: 1 GraphQL point (vs 1+ Search API calls per page).
        """
        from datetime import timezone as dt_timezone

        # GitHub GraphQL DateTime requires timezone-aware ISO 8601
        if start_date.tzinfo is None:
            from_dt = start_date.replace(tzinfo=dt_timezone.utc).isoformat()
        else:
            from_dt = start_date.isoformat()

        if end_date.tzinfo is None:
            to_dt = end_date.replace(tzinfo=dt_timezone.utc).isoformat()
        else:
            to_dt = end_date.isoformat()

        query = """
        query ContributionSummary($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            id
            contributionsCollection(from: $from, to: $to) {
              totalCommitContributions
              totalPullRequestContributions
              commitContributionsByRepository(maxRepositories: 100) {
                repository {
                  name
                  owner { login }
                }
                contributions { totalCount }
              }
              contributionCalendar {
                weeks {
                  contributionDays {
                    date
                    contributionCount
                  }
                }
              }
            }
          }
        }
        """

        variables = {"login": username, "from": from_dt, "to": to_dt}
        data = await self._graphql_query(query, variables, token)

        if not data:
            logger.warning(f"⚠️ [GRAPHQL] No contribution data returned for {username}")
            return None

        user_data = data.get("user")
        if not user_data:
            logger.warning(f"⚠️ [GRAPHQL] User '{username}' not found in GitHub")
            return None

        # GitHub node ID — used to filter commit history by user identity (not email)
        github_node_id = user_data.get("id")

        contributions = user_data.get("contributionsCollection", {})
        total_commits = contributions.get("totalCommitContributions", 0)
        total_prs = contributions.get("totalPullRequestContributions", 0)

        # Build daily counts from contribution calendar
        daily_counts = {}
        for week in contributions.get("contributionCalendar", {}).get("weeks", []):
            for day in week.get("contributionDays", []):
                date_str = day.get("date")
                count = day.get("contributionCount", 0)
                if date_str and count > 0:
                    daily_counts[date_str] = count

        # Build top repos list sorted by contribution count
        top_repos = []
        for repo_entry in contributions.get("commitContributionsByRepository", []):
            repo = repo_entry.get("repository", {})
            count = repo_entry.get("contributions", {}).get("totalCount", 0)
            owner = repo.get("owner", {}).get("login", "")
            name = repo.get("name", "")
            if owner and name and count > 0:
                top_repos.append({"owner": owner, "name": name, "count": count})
        top_repos.sort(key=lambda r: r["count"], reverse=True)

        logger.info(
            f"📊 [GRAPHQL_CONTRIBUTIONS] {username}: {total_commits} commits, "
            f"{total_prs} PRs, {len(top_repos)} repos with activity"
        )

        return {
            "total_commits": total_commits,
            "total_prs": total_prs,
            "daily_counts": daily_counts,
            "top_repos": top_repos,
            "github_node_id": github_node_id  # Used for accurate commit author filtering
        }

    async def _fetch_repo_commit_timestamps(self, owner: str, repo: str, user_id: str, since: str, until: str, token: str, max_commits: int = 10000) -> List[str]:
        """
        Fetch commit timestamps for a user from one repository using GraphQL.
        Filters by GitHub node ID (user.id) so ALL of this user's commits are returned
        regardless of which email address they used to commit.
        Paginates until all commits fetched or max_commits reached.

        Returns list of ISO timestamp strings (committedDate).
        Cost: ~1 point per 100 commits returned.
        """
        query = """
        query RepoTimestamps($owner: String!, $name: String!, $since: GitTimestamp!, $until: GitTimestamp!, $userId: ID!, $after: String) {
          repository(owner: $owner, name: $name) {
            defaultBranchRef {
              target {
                ... on Commit {
                  history(since: $since, until: $until, first: 100, after: $after,
                          author: { id: $userId }) {
                    nodes { committedDate }
                    pageInfo { hasNextPage endCursor }
                  }
                }
              }
            }
          }
        }
        """

        timestamps = []
        cursor = None

        while len(timestamps) < max_commits:
            variables = {
                "owner": owner,
                "name": repo,
                "since": since,
                "until": until,
                "userId": user_id,
                "after": cursor
            }

            data = await self._graphql_query(query, variables, token)
            if not data or self._rate_limited:
                break

            repo_data = data.get("repository")
            if not repo_data:
                break

            default_branch = repo_data.get("defaultBranchRef")
            if not default_branch:
                break  # Empty repo or no default branch

            history = default_branch.get("target", {}).get("history", {})
            nodes = history.get("nodes", [])
            page_info = history.get("pageInfo", {})

            for node in nodes:
                committed_date = node.get("committedDate")
                if committed_date:
                    timestamps.append(committed_date)

            if not page_info.get("hasNextPage") or not nodes:
                break

            cursor = page_info.get("endCursor")

        return timestamps

    async def fetch_daily_commit_data_graphql(self, username: str, email: str, start_date: datetime, end_date: datetime, token: str, timezone: str = 'UTC') -> tuple:
        """
        Fetch daily commit data using GitHub GraphQL API instead of REST Search API.

        GraphQL rate limit: 5,000 points/hour (vs Search API: 30 requests/MINUTE)
        Same Personal Access Token works — no token change needed.

        Returns:
            Tuple of (daily_data_list, total_commits, total_prs)
            - daily_data_list: same format as fetch_daily_commit_data()
            - total_commits: total commits in the period
            - total_prs: total PRs in the period
        """
        # Build empty daily structure covering the full date range
        daily_commits = {}
        current = start_date
        while current <= end_date:
            date_str = current.strftime('%Y-%m-%d')
            daily_commits[date_str] = {
                'date': date_str,
                'total_commits': 0,
                'after_hours_commits': 0,
                'weekend_commits': 0
            }
            current += timedelta(days=1)

        # Step 1: Contribution summary — 1 GraphQL point
        summary = await self._fetch_contributions_summary(username, start_date, end_date, token)
        if not summary:
            logger.warning(f"⚠️ [GRAPHQL] Could not fetch contributions for {username}, returning empty data")
            return (list(daily_commits.values()), 0, 0, [], 0)

        total_commits = summary["total_commits"]
        total_prs = summary["total_prs"]
        github_node_id = summary.get("github_node_id")

        # Fill daily totals from contribution calendar
        for date_str, count in summary["daily_counts"].items():
            if date_str in daily_commits:
                daily_commits[date_str]["total_commits"] = count

        repos_count = len(summary.get("top_repos", []))

        if total_commits == 0:
            logger.info(f"📊 [GRAPHQL] {username}: 0 commits in period")
            return (sorted(daily_commits.values(), key=lambda x: x['date']), 0, total_prs, [], repos_count)

        if not github_node_id:
            logger.warning(f"⚠️ [GRAPHQL] No GitHub node ID for {username} — cannot filter timestamps by user, skipping after-hours data")
            return (sorted(daily_commits.values(), key=lambda x: x['date']), total_commits, total_prs, [], repos_count)

        # Step 2: Fetch commit timestamps from top repos for after_hours/weekend classification
        # Uses GitHub node ID (not email) to match commits regardless of which email the user committed with
        since_iso = (start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                     if start_date.tzinfo is None else start_date.isoformat())
        until_iso = (end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
                     if end_date.tzinfo is None else end_date.isoformat())

        all_timestamps = []
        for repo_info in summary.get("top_repos", []):
            if self._rate_limited:
                logger.warning(f"⚠️ [GRAPHQL] Rate limited mid-fetch for {username} — using partial timestamp data")
                break

            owner = repo_info.get("owner", "")
            repo_name = repo_info.get("name", "")
            if not owner or not repo_name:
                continue

            logger.debug(f"🔍 [GRAPHQL] Fetching timestamps from {owner}/{repo_name} for {username} (node_id={github_node_id})")
            timestamps = await self._fetch_repo_commit_timestamps(
                owner=owner,
                repo=repo_name,
                user_id=github_node_id,
                since=since_iso,
                until=until_iso,
                token=token
            )
            all_timestamps.extend(timestamps)
            logger.debug(f"📊 [GRAPHQL] Got {len(timestamps)} timestamps from {owner}/{repo_name}")

        # Step 3: Classify timestamps into after_hours / weekend using user's timezone
        try:
            tz = pytz.timezone(timezone)
        except Exception:
            logger.warning(f"Invalid timezone '{timezone}' for {username}, using UTC")
            tz = pytz.UTC

        for ts in all_timestamps:
            try:
                dt_utc = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                dt_local = dt_utc.astimezone(tz)
                date_str = dt_local.strftime('%Y-%m-%d')

                if date_str not in daily_commits:
                    continue

                if dt_local.hour < self.business_hours['start'] or dt_local.hour >= self.business_hours['end']:
                    daily_commits[date_str]['after_hours_commits'] += 1
                if dt_local.weekday() >= 5:  # Saturday=5, Sunday=6
                    daily_commits[date_str]['weekend_commits'] += 1
            except Exception as ts_err:
                logger.debug(f"Could not parse timestamp {ts}: {ts_err}")
                continue

        sampled_count = len(all_timestamps)
        if sampled_count == 0 and total_commits > 0:
            logger.warning(
                f"⚠️ [GRAPHQL] {username}: {total_commits} commits found but no timestamps retrieved "
                f"(possible causes: private repos, no defaultBranchRef, rate limit, or API error) — after-hours data unavailable"
            )

        daily_data = sorted(daily_commits.values(), key=lambda x: x['date'])

        total_after = sum(d['after_hours_commits'] for d in daily_data)
        total_weekend = sum(d['weekend_commits'] for d in daily_data)
        logger.info(
            f"✅ [GRAPHQL] {username}: {total_commits} commits, {total_prs} PRs, "
            f"{total_after} after-hours, {total_weekend} weekend"
        )

        return (daily_data, total_commits, total_prs, all_timestamps, repos_count)

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

        if github_username:
            logger.info(f"✅ [SYNC_STATUS] Using cached GitHub mapping for {user_email}: {github_username}")
        else:
            logger.warning(f"⚠️ [SYNC_STATUS] No GitHub mapping for {user_email}. Sync required in Management page.")
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

    # Log GitHub Search rate-limit status once before processing any users.
    # Checks the 'search' bucket (30 req/min) — NOT the core bucket (5000/hr).
    if github_token and team_emails:
        try:
            import aiohttp
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'User-Agent': 'Rootly-Burnout-Detector'
            }
            async with aiohttp.ClientSession() as _sess:
                async with _sess.get("https://api.github.com/rate_limit", headers=headers) as resp:
                    if resp.status == 200:
                        rl_data = await resp.json()
                        search = rl_data.get('resources', {}).get('search', {})
                        remaining = search.get('remaining', '?')
                        limit = search.get('limit', 30)
                        reset_ts = search.get('reset')
                        if reset_ts:
                            reset_str = datetime.fromtimestamp(reset_ts).strftime('%H:%M:%S')
                            secs_left = max(0, int(reset_ts - datetime.now().timestamp()))
                            mins, secs = divmod(secs_left, 60)
                        else:
                            reset_str = 'unknown'
                            mins = secs = 0

                        if remaining == 0:
                            logger.warning(
                                f"⏳ [GITHUB_RATE_LIMIT] Search API exhausted — "
                                f"resets at {reset_str} (in {mins}m {secs}s). "
                                f"All {len(team_emails)} users will be skipped."
                            )
                            collector._rate_limited = True
                            collector._rate_limit_reset = str(reset_ts)
                        else:
                            logger.info(
                                f"📊 [GITHUB_RATE_LIMIT] Search API: {remaining}/{limit} requests remaining "
                                f"(resets at {reset_str} in {mins}m {secs}s) — "
                                f"about to process {len(team_emails)} users"
                            )
        except Exception as _e:
            logger.debug(f"Could not fetch rate limit status: {_e}")

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
            # Abort early if a previous user exhausted the GitHub Search rate limit.
            # Continuing would just produce 403s for every remaining user.
            if collector._rate_limited:
                from datetime import datetime as _dt
                try:
                    reset_readable = _dt.fromtimestamp(int(collector._rate_limit_reset)).strftime('%H:%M:%S') if collector._rate_limit_reset else 'unknown'
                except (ValueError, TypeError):
                    reset_readable = str(collector._rate_limit_reset)
                logger.warning(f"⏭️ [RATE_LIMIT] Skipping {email} — GitHub Search rate limit exhausted (resets at {reset_readable})")
                continue

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
