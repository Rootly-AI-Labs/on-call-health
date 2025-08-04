"""
Enhanced GitHub username matching algorithm with multiple strategies.
"""
import re
import logging
from typing import Optional, Dict, List, Set, Tuple
from difflib import SequenceMatcher
import aiohttp
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class EnhancedGitHubMatcher:
    """
    Enhanced matcher that uses multiple strategies to correlate emails to GitHub usernames.
    Strategies include:
    1. Direct email match from GitHub API
    2. Username pattern matching (firstname.lastname, firstlast, etc.)
    3. Fuzzy name matching
    4. Domain-specific patterns
    5. Commit history mining
    6. Organization member search
    """
    
    def __init__(self, github_token: str, organizations: List[str] = None):
        self.github_token = github_token
        self.organizations = organizations or []
        self.headers = {
            'Authorization': f'token {github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Rootly-Burnout-Detector'
        }
        
        # Cache to avoid repeated API calls
        self._user_cache = {}
        self._email_cache = {}
        self._org_members_cache = {}
        
    async def match_email_to_github(self, email: str, full_name: Optional[str] = None) -> Optional[str]:
        """
        Main entry point - tries all strategies to find a GitHub username.
        
        Args:
            email: Email address to match
            full_name: Optional full name to help with matching
            
        Returns:
            GitHub username if found, None otherwise
        """
        email_lower = email.lower()
        
        # Check cache first
        if email_lower in self._email_cache:
            return self._email_cache[email_lower]
        
        # Extract name parts from email
        email_parts = self._extract_name_from_email(email)
        
        # Try strategies in order of accuracy
        strategies = [
            ("direct_api_search", self._search_by_email_api),
            ("exact_username_match", self._try_exact_username_patterns),
            ("org_member_search", self._search_org_members),
            ("commit_history", self._search_commit_history),
            ("fuzzy_name_match", self._fuzzy_name_match),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"Trying {strategy_name} for {email}")
                
                if strategy_name == "direct_api_search":
                    result = await strategy_func(email)
                elif strategy_name in ["exact_username_match", "fuzzy_name_match"]:
                    result = await strategy_func(email_parts, full_name)
                else:
                    result = await strategy_func(email, email_parts)
                
                if result:
                    logger.info(f"✅ Found match via {strategy_name}: {email} -> {result}")
                    self._email_cache[email_lower] = result
                    return result
                    
            except Exception as e:
                logger.error(f"Error in {strategy_name}: {e}")
        
        logger.warning(f"❌ No GitHub match found for {email}")
        return None
    
    def _extract_name_from_email(self, email: str) -> Dict[str, str]:
        """Extract potential name components from email."""
        local_part = email.split('@')[0]
        
        # Remove common prefixes/suffixes
        for suffix in ['-rootly', '_rootly', '.rootly', '-admin', '_admin']:
            if local_part.endswith(suffix):
                local_part = local_part[:-len(suffix)]
        
        # Try different separators
        parts = {}
        
        # Split by dots
        if '.' in local_part:
            dot_parts = local_part.split('.')
            parts['firstname'] = dot_parts[0]
            parts['lastname'] = dot_parts[-1] if len(dot_parts) > 1 else ''
            parts['middlename'] = '.'.join(dot_parts[1:-1]) if len(dot_parts) > 2 else ''
        
        # Split by underscores
        elif '_' in local_part:
            underscore_parts = local_part.split('_')
            parts['firstname'] = underscore_parts[0]
            parts['lastname'] = underscore_parts[-1] if len(underscore_parts) > 1 else ''
        
        # Split by hyphens
        elif '-' in local_part:
            hyphen_parts = local_part.split('-')
            parts['firstname'] = hyphen_parts[0]
            parts['lastname'] = hyphen_parts[-1] if len(hyphen_parts) > 1 else ''
        
        # No separator - try camelCase
        else:
            # Look for capital letters
            capitals = [(i, c) for i, c in enumerate(local_part) if c.isupper()]
            if len(capitals) >= 2:
                parts['firstname'] = local_part[:capitals[1][0]].lower()
                parts['lastname'] = local_part[capitals[1][0]:].lower()
            else:
                parts['firstname'] = local_part
                parts['lastname'] = ''
        
        parts['full'] = local_part
        parts['email'] = email
        
        return parts
    
    async def _search_by_email_api(self, email: str) -> Optional[str]:
        """Search GitHub users by email using the search API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Search users by email
                search_url = f"https://api.github.com/search/users?q={email}+in:email"
                async with session.get(search_url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('total_count', 0) > 0:
                            username = data['items'][0]['login']
                            # Verify by checking user details
                            if await self._verify_user_email(username, email):
                                return username
                
                # Try commits search
                search_url = f"https://api.github.com/search/commits?q=author-email:{email}"
                headers_with_preview = self.headers.copy()
                headers_with_preview['Accept'] = 'application/vnd.github.cloak-preview+json'
                
                async with session.get(search_url, headers=headers_with_preview) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('total_count', 0) > 0:
                            # Get the author from the first commit
                            commit = data['items'][0]
                            if commit.get('author'):
                                return commit['author']['login']
                                
        except Exception as e:
            logger.error(f"Error in email API search: {e}")
        
        return None
    
    async def _try_exact_username_patterns(self, email_parts: Dict[str, str], full_name: Optional[str] = None) -> Optional[str]:
        """Try common username patterns based on email/name."""
        patterns = []
        
        firstname = email_parts.get('firstname', '')
        lastname = email_parts.get('lastname', '')
        
        if firstname and lastname:
            patterns.extend([
                f"{firstname}{lastname}",           # johnsmith
                f"{firstname}.{lastname}",          # john.smith
                f"{firstname}-{lastname}",          # john-smith
                f"{firstname}_{lastname}",          # john_smith
                f"{lastname}{firstname}",           # smithjohn
                f"{firstname[0]}{lastname}",        # jsmith
                f"{firstname}{lastname[0]}",        # johns
                f"{lastname}.{firstname}",          # smith.john
            ])
        
        if firstname:
            patterns.extend([
                firstname,                          # john
                f"{firstname}dev",                  # johndev
                f"{firstname}code",                 # johncode
                f"{firstname}123",                  # john123
            ])
        
        # Add full email local part
        patterns.append(email_parts.get('full', ''))
        
        # Try patterns from full name if provided
        if full_name:
            name_parts = full_name.lower().split()
            if len(name_parts) >= 2:
                patterns.extend([
                    ''.join(name_parts),            # fullname
                    '.'.join(name_parts),           # first.last
                    '-'.join(name_parts),           # first-last
                ])
        
        # Remove duplicates and empty strings
        patterns = list(filter(None, list(dict.fromkeys(patterns))))
        
        # Check each pattern
        for pattern in patterns:
            if await self._check_github_user_exists(pattern):
                return pattern
                
        return None
    
    async def _search_org_members(self, email: str, email_parts: Dict[str, str]) -> Optional[str]:
        """Search organization members for matches."""
        if not self.organizations:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                all_members = set()
                
                # Get all organization members
                for org in self.organizations:
                    if org not in self._org_members_cache:
                        members = await self._get_org_members(org, session)
                        self._org_members_cache[org] = members
                    all_members.update(self._org_members_cache[org])
                
                # Check each member for email match
                for username in all_members:
                    if await self._verify_user_email(username, email):
                        return username
                
                # Try fuzzy matching on usernames
                firstname = email_parts.get('firstname', '').lower()
                lastname = email_parts.get('lastname', '').lower()
                
                best_match = None
                best_score = 0
                
                for username in all_members:
                    username_lower = username.lower()
                    
                    # Direct substring match
                    if firstname and firstname in username_lower:
                        score = len(firstname) / len(username_lower)
                        if lastname and lastname in username_lower:
                            score += len(lastname) / len(username_lower)
                        
                        if score > best_score:
                            best_score = score
                            best_match = username
                
                # Return if we have a good match (>50% similarity)
                if best_score > 0.5:
                    # Verify with commit check
                    if await self._check_user_commits_for_email(best_match, email):
                        return best_match
                        
        except Exception as e:
            logger.error(f"Error in org member search: {e}")
            
        return None
    
    async def _search_commit_history(self, email: str, email_parts: Dict[str, str]) -> Optional[str]:
        """Search recent commits across organizations for email matches."""
        if not self.organizations:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                for org in self.organizations:
                    # Get recent repos with activity
                    repos_url = f"https://api.github.com/orgs/{org}/repos?sort=pushed&per_page=10"
                    async with session.get(repos_url, headers=self.headers) as resp:
                        if resp.status != 200:
                            continue
                            
                        repos = await resp.json()
                        
                        for repo in repos[:5]:  # Check top 5 most active repos
                            # Search commits by email
                            commits_url = f"https://api.github.com/repos/{repo['full_name']}/commits"
                            
                            async with session.get(commits_url, headers=self.headers) as resp:
                                if resp.status != 200:
                                    continue
                                    
                                commits = await resp.json()
                                
                                for commit in commits:
                                    commit_email = commit.get('commit', {}).get('author', {}).get('email', '')
                                    if commit_email.lower() == email.lower():
                                        if commit.get('author'):
                                            return commit['author']['login']
                                            
        except Exception as e:
            logger.error(f"Error in commit history search: {e}")
            
        return None
    
    async def _fuzzy_name_match(self, email_parts: Dict[str, str], full_name: Optional[str] = None) -> Optional[str]:
        """Use fuzzy matching to find similar usernames."""
        if not self.organizations:
            return None
            
        candidates = []
        firstname = email_parts.get('firstname', '').lower()
        lastname = email_parts.get('lastname', '').lower()
        
        if not firstname:
            return None
            
        try:
            async with aiohttp.ClientSession() as session:
                # Collect all members
                all_members = set()
                for org in self.organizations:
                    if org in self._org_members_cache:
                        all_members.update(self._org_members_cache[org])
                    else:
                        members = await self._get_org_members(org, session)
                        all_members.update(members)
                
                # Score each member
                for username in all_members:
                    username_lower = username.lower()
                    
                    # Calculate similarity scores
                    firstname_score = SequenceMatcher(None, firstname, username_lower).ratio()
                    
                    total_score = firstname_score
                    if lastname:
                        lastname_score = SequenceMatcher(None, lastname, username_lower).ratio()
                        total_score = (firstname_score + lastname_score) / 2
                    
                    if total_score > 0.7:  # 70% similarity threshold
                        candidates.append((username, total_score))
                
                # Sort by score and check top candidates
                candidates.sort(key=lambda x: x[1], reverse=True)
                
                for username, score in candidates[:3]:
                    # Verify with additional checks
                    if await self._check_user_commits_for_email(username, email_parts['email']):
                        return username
                        
        except Exception as e:
            logger.error(f"Error in fuzzy name match: {e}")
            
        return None
    
    async def _check_github_user_exists(self, username: str) -> bool:
        """Check if a GitHub username exists."""
        if username in self._user_cache:
            return self._user_cache[username]
            
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://api.github.com/users/{username}"
                async with session.get(url, headers=self.headers) as resp:
                    exists = resp.status == 200
                    self._user_cache[username] = exists
                    return exists
        except Exception as e:
            logger.error(f"Error checking user {username}: {e}")
            return False
    
    async def _verify_user_email(self, username: str, email: str) -> bool:
        """Verify if a GitHub user has a specific email."""
        try:
            async with aiohttp.ClientSession() as session:
                # Check public profile
                url = f"https://api.github.com/users/{username}"
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('email', '').lower() == email.lower():
                            return True
                
                # Check recent commits
                return await self._check_user_commits_for_email(username, email)
                
        except Exception as e:
            logger.error(f"Error verifying email for {username}: {e}")
            return False
    
    async def _check_user_commits_for_email(self, username: str, email: str) -> bool:
        """Check if a user has commits with a specific email."""
        try:
            async with aiohttp.ClientSession() as session:
                # Get user's recent events
                events_url = f"https://api.github.com/users/{username}/events?per_page=10"
                async with session.get(events_url, headers=self.headers) as resp:
                    if resp.status != 200:
                        return False
                        
                    events = await resp.json()
                    
                    # Find repos with push events
                    repos = set()
                    for event in events:
                        if event.get('type') == 'PushEvent' and event.get('repo'):
                            repos.add(event['repo']['name'])
                    
                    # Check commits in recent repos
                    for repo in list(repos)[:2]:  # Check top 2 repos
                        commits_url = f"https://api.github.com/repos/{repo}/commits?author={username}&per_page=5"
                        async with session.get(commits_url, headers=self.headers) as resp:
                            if resp.status == 200:
                                commits = await resp.json()
                                for commit in commits:
                                    commit_email = commit.get('commit', {}).get('author', {}).get('email', '')
                                    if commit_email.lower() == email.lower():
                                        return True
                                        
        except Exception as e:
            logger.debug(f"Error checking commits for {username}: {e}")
            
        return False
    
    async def _get_org_members(self, org: str, session) -> Set[str]:
        """Get all members of an organization."""
        members = set()
        try:
            page = 1
            while True:
                url = f"https://api.github.com/orgs/{org}/members?per_page=100&page={page}"
                async with session.get(url, headers=self.headers) as resp:
                    if resp.status != 200:
                        break
                        
                    data = await resp.json()
                    if not data:
                        break
                        
                    members.update(member['login'] for member in data)
                    
                    # Check if there are more pages
                    if len(data) < 100:
                        break
                    page += 1
                    
        except Exception as e:
            logger.error(f"Error getting members for {org}: {e}")
            
        return members