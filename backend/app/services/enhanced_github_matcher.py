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
        # Validate email input
        if not email or not isinstance(email, str):
            logger.warning(f"Invalid email provided: {email}")
            return None
            
        email_lower = email.lower()
        
        # Check cache first
        if email_lower in self._email_cache:
            return self._email_cache[email_lower]
        
        # Extract name parts from email
        email_parts = self._extract_name_from_email(email)
        
        # Try strategies in order of accuracy - OPTIMIZED for speed
        # Skip expensive strategies during analysis to improve performance
        strategies = [
            ("direct_api_search", self._search_by_email_api),
            ("exact_username_match", self._try_exact_username_patterns),
            ("org_member_search", self._search_org_members),
            # Skip expensive strategies that cause slowdowns:
            # ("commit_history", self._search_commit_history),  # Too many API calls
            # ("fuzzy_name_match", self._fuzzy_name_match),     # Too many API calls
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"Trying {strategy_name} for {email}")
                
                # Add small delay to avoid hitting rate limits
                import asyncio
                await asyncio.sleep(0.1)  # 100ms delay between strategies
                
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
    
    async def match_name_to_github(self, full_name: str, fallback_email: Optional[str] = None) -> Optional[str]:
        """
        Match a full name to GitHub username using name-based strategies.
        
        Args:
            full_name: Full name to match (e.g., "Spencer Cheng")
            fallback_email: Optional email for additional context
            
        Returns:
            GitHub username if found, None otherwise
        """
        if not full_name or not isinstance(full_name, str):
            logger.warning(f"Invalid name provided: {full_name}")
            return None
            
        full_name_clean = full_name.strip()
        logger.info(f"🔍 Starting name-based matching for: '{full_name_clean}'")
        
        # Extract name parts for pattern matching
        name_parts = self._extract_name_parts_from_full_name(full_name_clean)
        
        # Try name-based strategies
        strategies = [
            ("exact_name_patterns", self._try_name_username_patterns),
            ("fuzzy_name_org_search", self._fuzzy_name_match_in_orgs),
            ("github_profile_search", self._search_github_by_name),
        ]
        
        for strategy_name, strategy_func in strategies:
            try:
                logger.info(f"Trying {strategy_name} for '{full_name_clean}'")
                
                # Add small delay to avoid hitting rate limits
                import asyncio
                await asyncio.sleep(0.1)
                
                result = await strategy_func(name_parts, full_name_clean, fallback_email)
                
                if result:
                    logger.info(f"✅ Found match via {strategy_name}: '{full_name_clean}' -> {result}")
                    return result
                    
            except Exception as e:
                logger.error(f"Error in {strategy_name}: {e}")
        
        logger.warning(f"❌ No GitHub match found for name: '{full_name_clean}'")
        return None
    
    def _extract_name_parts_from_full_name(self, full_name: str) -> Dict[str, str]:
        """Extract name components from full name."""
        # Clean the name
        clean_name = re.sub(r'[^\w\s-.]', '', full_name.strip())
        parts = clean_name.split()
        
        if len(parts) == 0:
            return {}
        elif len(parts) == 1:
            return {
                'first': parts[0].lower(),
                'last': '',
                'full_parts': parts
            }
        else:
            return {
                'first': parts[0].lower(),
                'last': parts[-1].lower(),
                'middle': ' '.join(parts[1:-1]).lower() if len(parts) > 2 else '',
                'full_parts': parts
            }
    
    async def _try_name_username_patterns(self, name_parts: Dict[str, str], full_name: str, fallback_email: Optional[str] = None) -> Optional[str]:
        """Try common username patterns based on the full name."""
        if not name_parts or not name_parts.get('first'):
            return None
            
        firstname = name_parts.get('first', '')
        lastname = name_parts.get('last', '')
        
        patterns = []
        
        if firstname and lastname:
            patterns.extend([
                f"{firstname}{lastname}",           # spencercheng
                f"{firstname}.{lastname}",          # spencer.cheng
                f"{firstname}-{lastname}",          # spencer-cheng  
                f"{firstname}_{lastname}",          # spencer_cheng
                f"{firstname[0]}{lastname}",        # scheng
                f"{firstname}{lastname[0]}",        # spencerc
                f"{lastname}{firstname}",           # chengspencer
                f"{firstname[0]}.{lastname}",       # s.cheng
                f"{firstname}.{lastname[0]}",       # spencer.c
            ])
        
        if firstname:
            patterns.extend([
                firstname,                          # spencer
                f"{firstname}dev",                  # spencerdev
                f"{firstname}code",                 # spencercode
                f"{firstname}123",                  # spencer123
                f"{firstname}-dev",                 # spencer-dev
            ])
        
        # Remove duplicates and empty strings
        patterns = list(filter(None, list(dict.fromkeys(patterns))))
        
        # Check each pattern - limit for performance
        for pattern in patterns[:8]:  # Limit to 8 API calls max
            if await self._check_github_user_exists(pattern):
                # Verify user is in our organizations
                if await self._verify_user_in_organizations(pattern):
                    # Optional: Additional verification using name similarity
                    if await self._verify_username_matches_name(pattern, full_name):
                        return pattern
                
        return None
    
    async def _fuzzy_name_match_in_orgs(self, name_parts: Dict[str, str], full_name: str, fallback_email: Optional[str] = None) -> Optional[str]:
        """Search organization members using fuzzy name matching."""
        if not self.organizations or not name_parts.get('first'):
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
                
                if not all_members:
                    return None
                
                # Get actual GitHub profiles to compare names
                firstname = name_parts.get('first', '').lower()
                lastname = name_parts.get('last', '').lower()
                candidates = []
                
                for username in all_members:
                    # Get user profile to check name
                    user_profile = await self._get_github_user_profile(username, session)
                    if not user_profile:
                        continue
                        
                    github_name = user_profile.get('name', '').lower()
                    if not github_name:
                        continue
                    
                    # Calculate name similarity
                    similarity_score = self._calculate_name_similarity(
                        full_name.lower(), 
                        github_name,
                        firstname,
                        lastname
                    )
                    
                    if similarity_score > 0.6:  # 60% similarity threshold
                        candidates.append((username, similarity_score, github_name))
                
                # Sort by similarity and return best match
                if candidates:
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    best_match = candidates[0]
                    logger.info(f"🎯 Best name match: {best_match[0]} (score: {best_match[1]:.2f}, github_name: '{best_match[2]}')")
                    return best_match[0]
                        
        except Exception as e:
            logger.error(f"Error in fuzzy name match: {e}")
            
        return None
    
    async def _search_github_by_name(self, name_parts: Dict[str, str], full_name: str, fallback_email: Optional[str] = None) -> Optional[str]:
        """Search GitHub users by name using the search API."""
        try:
            async with aiohttp.ClientSession() as session:
                # Search for users by name
                search_query = full_name.replace(' ', '+')
                search_url = f"https://api.github.com/search/users?q={search_query}+in:fullname"
                
                async with session.get(search_url, headers=self.headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('total_count', 0) > 0:
                            # Check each result
                            for item in data['items'][:5]:  # Check top 5 results
                                username = item['login']
                                
                                # Verify user is in our organizations
                                if await self._verify_user_in_organizations(username):
                                    # Get full profile for name verification
                                    user_profile = await self._get_github_user_profile(username, session)
                                    if user_profile and user_profile.get('name'):
                                        github_name = user_profile['name'].lower()
                                        if self._calculate_name_similarity(full_name.lower(), github_name, 
                                                                         name_parts.get('first', '').lower(),
                                                                         name_parts.get('last', '').lower()) > 0.7:
                                            return username
                
        except Exception as e:
            logger.error(f"Error in GitHub name search: {e}")
        
        return None
    
    async def _get_github_user_profile(self, username: str, session) -> Optional[Dict]:
        """Get GitHub user profile information."""
        try:
            url = f"https://api.github.com/users/{username}"
            async with session.get(url, headers=self.headers) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.debug(f"Error getting profile for {username}: {e}")
        return None
    
    def _calculate_name_similarity(self, full_name1: str, full_name2: str, firstname: str = "", lastname: str = "") -> float:
        """Calculate similarity between two full names."""
        # Direct string similarity
        direct_sim = SequenceMatcher(None, full_name1, full_name2).ratio()
        
        # Check if first/last names are contained in the GitHub name
        firstname_match = firstname in full_name2 if firstname else 0
        lastname_match = lastname in full_name2 if lastname else 0
        
        # Combine different similarity measures
        name_component_score = (firstname_match + lastname_match) / 2 if (firstname or lastname) else 0
        
        # Return weighted average
        return (direct_sim * 0.6) + (name_component_score * 0.4)
    
    async def _verify_username_matches_name(self, username: str, full_name: str) -> bool:
        """Verify that a username reasonably matches the given full name."""
        try:
            async with aiohttp.ClientSession() as session:
                user_profile = await self._get_github_user_profile(username, session)
                if user_profile and user_profile.get('name'):
                    github_name = user_profile['name'].lower()
                    similarity = self._calculate_name_similarity(full_name.lower(), github_name)
                    return similarity > 0.5  # 50% similarity threshold for verification
        except Exception as e:
            logger.debug(f"Error verifying name match for {username}: {e}")
        
        return True  # Default to True if we can't verify (don't be too strict)
    
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
                            # Verify by checking user details and org membership
                            if await self._verify_user_email(username, email):
                                # CRITICAL: Verify user is actually in our organizations
                                if await self._verify_user_in_organizations(username):
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
                                username = commit['author']['login']
                                # CRITICAL: Verify user is actually in our organizations
                                if await self._verify_user_in_organizations(username):
                                    return username
                                
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
        
        # Check each pattern - LIMIT to first 5 patterns for performance
        for pattern in patterns[:5]:  # Limit to 5 API calls max
            if await self._check_github_user_exists(pattern):
                # CRITICAL: Verify user is actually in our organizations
                if await self._verify_user_in_organizations(pattern):
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
                                            username = commit['author']['login']
                                            # Verify user is in our organizations
                                            if await self._verify_user_in_organizations(username):
                                                return username
                                            
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
                        # CRITICAL: Verify user is actually in our organizations
                        if await self._verify_user_in_organizations(username):
                            return username
                        
        except Exception as e:
            logger.error(f"Error in fuzzy name match: {e}")
            
        return None
    
    async def _verify_user_in_organizations(self, username: str) -> bool:
        """Verify that a user is a member of at least one of our specified organizations."""
        if not self.organizations:
            return True  # No org restrictions configured
            
        try:
            async with aiohttp.ClientSession() as session:
                for org in self.organizations:
                    # Get org members (use cache if available)
                    if org not in self._org_members_cache:
                        members = await self._get_org_members(org, session)
                        self._org_members_cache[org] = members
                    
                    if username in self._org_members_cache[org]:
                        logger.info(f"✅ User {username} verified as member of {org}")
                        return True
                        
                logger.warning(f"❌ User {username} is NOT a member of any specified organizations: {self.organizations}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying org membership for {username}: {e}")
            return False
    
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