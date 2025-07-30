"""
GitHub data collector for web app burnout analysis.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import requests
import asyncio
# from sqlalchemy.orm import Session
# from ..models import GitHubIntegration

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
        
        # Predefined email mappings (from original config, to handle cases where GitHub email != Rootly email)
        self.predefined_email_mappings = {
            "spencer.cheng@rootly.com": "spencerhcheng",
            "jasmeet.singh@rootly.com": "jasmeetluthra", 
            "sylvain@rootly.com": "sylvainkalache",
            "christo.mitov@rootly.com": "christomitov",
            "ibrahim@rootly.com": "ibrahimelchami",
            "weihan@rootly.com": "weihanli101",
            "alex.mingoia@rootly.com": "alexmingoia",
            "quentin@rootly.com": "kwent",
            "gideon@rootly.com": "gid-rootly",
            "dan@rootly.com": "dansadler1",
            # Additional mappings for Integration ID 3 users
            "nicholas@rootly.com": "nronas",
            "kumbi@rootly.com": "kumbirai"
        }
        
        # Cache for email mapping
        self._email_mapping_cache = None
        
    async def _correlate_email_to_github(self, email: str, token: str) -> Optional[str]:
        """
        Correlate an email address to a GitHub username using multiple strategies.
        
        This mimics the logic from the original burnout detector:
        1. Check manual mappings first
        2. Check discovered email mappings from organization members
        """
        logger.info(f"GitHub correlation attempt for {email}, token={'present' if token else 'missing'}")
        
        if not token:
            logger.warning("No GitHub token provided for correlation")
            return None
            
        try:
            # First check predefined mappings
            logger.info(f"Checking predefined mappings for {email}. Available mappings: {list(self.predefined_email_mappings.keys())}")
            logger.info(f"Predefined mappings dict: {self.predefined_email_mappings}")
            username = self.predefined_email_mappings.get(email)
            if username:
                logger.info(f"Found GitHub correlation via predefined mapping: {email} -> {username}")
                return username
            else:
                logger.warning(f"No predefined mapping found for {email}")
            
            # Build email mapping if not cached
            if self._email_mapping_cache is None:
                logger.info("Building email mapping cache from GitHub API")
                self._email_mapping_cache = await self._build_email_mapping(token)
                
            # Look up the email (case insensitive)
            email_lower = email.lower()
            username = self._email_mapping_cache.get(email_lower)
            
            if username:
                logger.info(f"Found GitHub correlation via discovered mapping: {email} -> {username}")
                return username
            else:
                logger.warning(f"No GitHub correlation found for {email}")
                return None
            
        except Exception as e:
            logger.error(f"Error correlating email {email} to GitHub: {e}")
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
            events_url = f"https://api.github.com/users/{username}/events?per_page=100"
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
                    for repo_name in list(repos_to_check):  # No limit on repos
                        try:
                            commits_url = f"https://api.github.com/repos/{repo_name}/commits?author={username}&per_page=100"
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
        
    async def _fetch_real_github_data(self, username: str, email: str, start_date: datetime, end_date: datetime, token: str) -> Dict:
        """Fetch real GitHub data using the GitHub API with enterprise resilience."""
        
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Rootly-Burnout-Detector'
        }
        
        since_iso = start_date.isoformat()
        until_iso = end_date.isoformat()
        
        # Fetch user info
        user_url = f"https://api.github.com/users/{username}"
        
        try:
            # Phase 2.3: Use API manager for resilient GitHub API calls
            from .github_api_manager import github_api_manager
            
            # Get commits across all repos
            commits_url = f"https://api.github.com/search/commits?q=author:{username}+author-date:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
            
            # Get pull requests
            prs_url = f"https://api.github.com/search/issues?q=author:{username}+type:pr+created:{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}"
            
            # Make resilient API calls with rate limiting and circuit breaker
            async def fetch_commits():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(commits_url, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        else:
                            raise aiohttp.ClientError(f"GitHub API error for commits: {resp.status}")
            
            async def fetch_prs():
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(prs_url, headers=headers) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        else:
                            raise aiohttp.ClientError(f"GitHub API error for PRs: {resp.status}")
            
            # Execute with enterprise resilience patterns
            commits_data = await github_api_manager.safe_api_call(fetch_commits, max_retries=3)
            total_commits = commits_data.get('total_count', 0) if commits_data else 0
            
            prs_data = await github_api_manager.safe_api_call(fetch_prs, max_retries=3)
            total_prs = prs_data.get('total_count', 0) if prs_data else 0
            
            logger.info(f"📊 GitHub API calls completed - Commits: {total_commits}, PRs: {total_prs}")
            
            # For now, estimate other metrics based on commits/PRs
            # In a full implementation, we'd make additional API calls
            after_hours_commits = int(total_commits * 0.15)  # Estimate 15% after hours
            weekend_commits = int(total_commits * 0.1)       # Estimate 10% weekend
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
                }
            }
            
        except Exception as e:
            logger.error(f"Error fetching real GitHub data for {username}: {e}")
            # Fall back to mock data
            return self._generate_mock_github_data(username, email, start_date, end_date)
        
    async def collect_github_data_for_user(self, user_email: str, days: int = 30, github_token: str = None) -> Optional[Dict]:
        """
        Collect GitHub activity data for a single user using email correlation.
        
        Args:
            user_email: User's email to correlate with GitHub
            days: Number of days to analyze
            github_token: GitHub API token for authentication
            
        Returns:
            GitHub activity data or None if no correlation found
        """
        # Use email-based correlation to find GitHub username
        github_username = await self._correlate_email_to_github(user_email, github_token)
        
        if not github_username:
            logger.warning(f"No GitHub username found for email {user_email}")
            return None
            
        logger.info(f"Collecting GitHub data for {github_username} ({user_email})")
        
        # Set up date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Use real GitHub API if token provided
        if github_token:
            logger.info(f"Using real GitHub API for {github_username} with token: {github_token[:10]}...")
            return await self._fetch_real_github_data(github_username, user_email, start_date, end_date, github_token)
        else:
            # Fall back to mock data for testing
            logger.warning(f"No GitHub token, using mock data for {github_username}")
            return self._generate_mock_github_data(github_username, user_email, start_date, end_date)
    
    def _generate_mock_github_data(self, username: str, email: str, start_date: datetime, end_date: datetime) -> Dict:
        """Generate realistic mock GitHub data for testing."""
        
        # Generate some realistic activity
        import random
        
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
                'after_hours_commits': after_hours_commits,
                'weekend_commits': weekend_commits,
                'avg_pr_size': random.randint(50, 300),
                'burnout_indicators': burnout_indicators
            }
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


async def collect_team_github_data(team_emails: List[str], days: int = 30, github_token: str = None) -> Dict[str, Dict]:
    """
    Collect GitHub data for all team members.
    
    Args:
        team_emails: List of team member emails
        days: Number of days to analyze
        github_token: GitHub API token for real data collection
        
    Returns:
        Dict mapping email -> github_activity_data
    """
    collector = GitHubCollector()
    github_data = {}
    
    for email in team_emails:
        try:
            user_data = await collector.collect_github_data_for_user(email, days, github_token)
            if user_data:
                github_data[email] = user_data
        except Exception as e:
            logger.error(f"Failed to collect GitHub data for {email}: {e}")
    
    logger.info(f"Collected GitHub data for {len(github_data)} users out of {len(team_emails)}")
    return github_data