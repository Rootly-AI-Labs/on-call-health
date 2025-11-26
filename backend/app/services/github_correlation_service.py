"""
GitHub Data Correlation Service V2 - Uses integration_mappings as primary source
This fixes the issue where only top_contributors (5 users) were used instead of all successful mappings (10+ users)
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from sqlalchemy import create_engine, text
import os

logger = logging.getLogger(__name__)


class GitHubCorrelationService:
    """
    Enhanced correlation service that uses integration_mappings table as primary source
    This gives us ALL successful GitHub mappings, not just the top 5 contributors
    """
    
    def __init__(self, current_user_id: Optional[int] = None):
        self.logger = logger
        self.current_user_id = current_user_id
        
    def correlate_github_data(
        self, 
        team_members: List[Dict[str, Any]], 
        github_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Correlate GitHub data with team members using integration_mappings as primary source
        Falls back to top_contributors if integration_mappings unavailable
        
        Args:
            team_members: List of team member dicts from team_analysis
            github_insights: GitHub insights dict containing top_contributors
            
        Returns:
            Updated team_members list with populated github_activity fields
        """
        try:
            # Try integration_mappings-driven correlation first (preferred method)
            if self.current_user_id:
                return self._correlate_with_integration_mappings(team_members, github_insights)
            
            # Fallback to top_contributors correlation (original method)
            return self._correlate_with_top_contributors(team_members, github_insights)
            
        except Exception as e:
            self.logger.error(f"Error in GitHub correlation: {e}")
            return team_members
    
    def _correlate_with_integration_mappings(
        self, 
        team_members: List[Dict[str, Any]], 
        github_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Correlate using integration_mappings table - this gives us ALL successful mappings (10+), not just top 5
        """
        try:
            # Get all successful GitHub mappings from integration_mappings table
            github_mappings = self._fetch_integration_mappings()
            
            if not github_mappings:
                self.logger.warning("No GitHub integration mappings found, falling back to top_contributors")
                return self._correlate_with_top_contributors(team_members, github_insights)
            
            self.logger.info(f"Found {len(github_mappings)} successful GitHub mappings in integration_mappings")
            
            # Create mapping dictionary: email -> github_data
            email_to_github = {}
            for mapping in github_mappings:
                email = mapping['email'].lower().strip()
                email_to_github[email] = mapping
                self.logger.info(f"Integration mapping: {email} → {mapping['username']} (data points: {mapping.get('data_points', 0)})")
            
            # Correlate with team members
            correlations_made = 0
            updated_members = []
            
            for member in team_members:
                if not isinstance(member, dict):
                    updated_members.append(member)
                    continue
                
                member_email = member.get('user_email', '').lower().strip()
                
                # Check if this member has an integration mapping
                if member_email in email_to_github:
                    github_mapping = email_to_github[member_email]

                    # IMPORTANT: Don't overwrite existing github_activity if it already has real data
                    existing_github_activity = member.get('github_activity', {})
                    existing_commits = existing_github_activity.get('commits_count', 0) if existing_github_activity else 0

                    if existing_commits > 0:
                        # Member already has real GitHub data from collection phase - don't overwrite!
                        self.logger.info(f"✅ Skipping correlation for {member_email} - already has real GitHub data ({existing_commits} commits)")
                        updated_members.append(member)
                    else:
                        # No existing data, create from integration mapping
                        github_activity = self._create_github_activity_from_integration_mapping(github_mapping)

                        if github_activity:
                            # Update member with GitHub data
                            updated_member = member.copy()
                            updated_member['github_activity'] = github_activity
                            updated_member['github_username'] = github_mapping['username']
                            updated_member['github_commits'] = github_activity.get('commits_count', 0)
                            updated_member['github_commits_per_week'] = github_activity.get('commits_per_week', 0)

                            updated_members.append(updated_member)
                            correlations_made += 1

                            self.logger.info(f"✅ Correlated {member_email} → {github_mapping['username']} ({github_activity.get('commits_count', 0)} commits)")
                        else:
                            # Mapping exists but no activity data
                            updated_members.append(member)
                            self.logger.warning(f"⚠️ Integration mapping exists for {member_email} → {github_mapping['username']} but no activity data")
                else:
                    # No mapping for this member
                    updated_members.append(member)
            
            self.logger.info(f"Integration-driven GitHub correlation completed: {correlations_made}/{len(github_mappings)} mappings used for team members")
            return updated_members
            
        except Exception as e:
            self.logger.error(f"Error in integration-driven correlation: {e}")
            # Fallback to top_contributors method
            return self._correlate_with_top_contributors(team_members, github_insights)
    
    def _fetch_integration_mappings(self) -> List[Dict[str, Any]]:
        """
        Fetch successful GitHub mappings from BOTH integration_mappings and user_mappings tables
        """
        try:
            # Use DATABASE_URL environment variable
            database_url = os.getenv('DATABASE_URL')
            if not database_url:
                self.logger.error("DATABASE_URL environment variable not set")
                return []
            
            engine = create_engine(database_url)
            conn = engine.connect()
            
            mappings = []
            
            # First, get mappings from integration_mappings table (auto-detected)
            query1 = """
                SELECT source_identifier, target_identifier, data_points_count, 
                       mapping_successful, created_at, 'auto' as mapping_source
                FROM integration_mappings 
                WHERE target_platform = 'github' 
                  AND mapping_successful = true
                  AND target_identifier IS NOT NULL
                  AND target_identifier != 'None'
            """
            
            params = {}
            if self.current_user_id:
                query1 += " AND user_id = :user_id"
                params['user_id'] = self.current_user_id
            
            query1 += " ORDER BY created_at DESC"
            
            result1 = conn.execute(text(query1), params)
            auto_mappings = result1.fetchall()
            
            # Process auto-detected mappings
            seen_emails = set()
            for row in auto_mappings:
                email, username, data_points, successful, created_at, source = row
                email_lower = email.lower()
                if email_lower not in seen_emails:
                    mappings.append({
                        'email': email,
                        'username': username,
                        'data_points': data_points or 0,
                        'mapping_successful': successful,
                        'created_at': created_at,
                        'source': 'auto_detected'
                    })
                    seen_emails.add(email_lower)
            
            # Second, get manual mappings from user_mappings table
            query2 = """
                SELECT source_identifier, target_identifier, created_at
                FROM user_mappings
                WHERE source_platform = 'rootly'
                  AND target_platform = 'github'
                  AND target_identifier IS NOT NULL
                  AND target_identifier != ''
            """
            
            if self.current_user_id:
                query2 += " AND user_id = :user_id"
            
            query2 += " ORDER BY created_at DESC"
            
            result2 = conn.execute(text(query2), params)
            manual_mappings = result2.fetchall()
            
            # Process manual mappings, preferring them over auto-detected
            for row in manual_mappings:
                email, username, created_at = row
                email_lower = email.lower()
                
                # Remove any existing auto-detected mapping for this email
                mappings = [m for m in mappings if m['email'].lower() != email_lower]
                
                # Add the manual mapping
                mappings.append({
                    'email': email,
                    'username': username,
                    'data_points': 0,  # Will be fetched when collecting data
                    'mapping_successful': True,
                    'created_at': created_at,
                    'source': 'manual'
                })
                seen_emails.add(email_lower)
            
            conn.close()
            
            self.logger.info(f"Fetched {len(mappings)} total GitHub mappings:")
            self.logger.info(f"  - Auto-detected: {len([m for m in mappings if m['source'] == 'auto_detected'])}")
            self.logger.info(f"  - Manual: {len([m for m in mappings if m['source'] == 'manual'])}")
            
            # Log manual mappings for debugging
            for mapping in mappings:
                if mapping['source'] == 'manual':
                    self.logger.info(f"  Manual mapping: {mapping['email']} → {mapping['username']}")
            
            return mappings
            
        except Exception as e:
            self.logger.error(f"Error fetching mappings: {e}")
            return []
    
    def _create_github_activity_from_integration_mapping(self, mapping: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create github_activity dict from integration mapping data
        
        Args:
            mapping: Single mapping from integration_mappings table
            
        Returns:
            Standardized github_activity dict
        """
        try:
            username = mapping.get('username', '')
            data_points = mapping.get('data_points', 0)
            email = mapping.get('email', '')
            
            # If we have data points, use them; otherwise create a basic structure
            if data_points > 0:
                # Estimate metrics based on data points (could be refined with actual API data)
                estimated_commits = data_points
                estimated_prs = max(1, int(data_points * 0.15))  # ~15% of activity results in PRs
                estimated_reviews = max(1, int(data_points * 0.25))  # ~25% review rate
                commits_per_week = round(data_points / 4.3, 2)  # Approximate weeks in a month
            else:
                # Mapping exists but no data collected
                estimated_commits = 0
                estimated_prs = 0
                estimated_reviews = 0
                commits_per_week = 0
            
            # Calculate burnout indicators
            burnout_indicators = self._calculate_github_burnout_indicators(
                estimated_commits, commits_per_week
            )
            
            github_activity = {
                'commits_count': estimated_commits,
                'pull_requests_count': estimated_prs,
                'reviews_count': estimated_reviews,
                'after_hours_commits': int(estimated_commits * 0.1),  # 10% estimate
                'weekend_commits': int(estimated_commits * 0.05),  # 5% estimate
                'commits_per_week': commits_per_week,
                'avg_pr_size': 50,  # Default estimate
                'username': username,
                'email': email,
                'burnout_indicators': burnout_indicators,
                'last_updated': datetime.now().isoformat(),
                'data_source': 'integration_mappings',
                'data_points_available': data_points,
                'mapping_status': 'successful_with_data' if data_points > 0 else 'successful_no_data'
            }
            
            return github_activity
            
        except Exception as e:
            self.logger.error(f"Error creating GitHub activity from integration mapping: {e}")
            return {
                'commits_count': 0,
                'pull_requests_count': 0,
                'reviews_count': 0,
                'after_hours_commits': 0,
                'weekend_commits': 0,
                'burnout_indicators': {
                    'excessive_commits': False,
                    'late_night_activity': False,
                    'weekend_work': False,
                    'large_prs': False
                },
                'data_source': 'integration_mappings_error',
                'mapping_status': 'error'
            }
    
    def _correlate_with_top_contributors(
        self, 
        team_members: List[Dict[str, Any]], 
        github_insights: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Fallback method: Correlate using top_contributors data (original method)
        """
        try:
            # Extract top contributors
            top_contributors = github_insights.get('top_contributors', [])
            if not top_contributors or not isinstance(top_contributors, list):
                self.logger.warning("No top_contributors found in GitHub insights")
                return team_members
            
            # Create email-to-github mapping
            github_by_email = {}
            for contributor in top_contributors:
                if isinstance(contributor, dict):
                    email = contributor.get('email', '').lower().strip()
                    if email:
                        github_by_email[email] = contributor
            
            self.logger.info(f"GitHub correlation (fallback): Found {len(github_by_email)} contributors with emails")
            
            # Correlate with team members
            correlations_made = 0
            updated_members = []
            
            for member in team_members:
                if not isinstance(member, dict):
                    updated_members.append(member)
                    continue
                
                # Get member email
                member_email = member.get('user_email', '').lower().strip()
                
                # Try to find GitHub data for this member
                if member_email and member_email in github_by_email:
                    github_data = github_by_email[member_email]
                    
                    # Create comprehensive github_activity data
                    github_activity = self._create_github_activity_from_contributor_data(github_data)
                    
                    # Update member with GitHub data
                    updated_member = member.copy()
                    updated_member['github_activity'] = github_activity
                    
                    # Also add some top-level GitHub fields for easier access
                    updated_member['github_username'] = github_data.get('username', '')
                    updated_member['github_commits'] = github_data.get('total_commits', 0)
                    updated_member['github_commits_per_week'] = github_data.get('commits_per_week', 0)
                    
                    updated_members.append(updated_member)
                    correlations_made += 1
                    
                    self.logger.info(f"Correlated (fallback) {member_email} → {github_data.get('username')} ({github_data.get('total_commits')} commits)")
                    
                else:
                    # No GitHub data found - keep member as is
                    updated_members.append(member)
            
            self.logger.info(f"GitHub correlation (fallback) completed: {correlations_made}/{len(team_members)} members correlated")
            
            return updated_members
            
        except Exception as e:
            self.logger.error(f"Error in fallback GitHub correlation: {e}")
            return team_members
    
    def _create_github_activity_from_contributor_data(self, github_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create github_activity dict from top_contributor data (fallback method)
        """
        try:
            total_commits = github_data.get('total_commits', 0)
            commits_per_week = github_data.get('commits_per_week', 0)
            
            # Calculate derived metrics
            estimated_prs = max(1, int(total_commits * 0.15))
            estimated_reviews = max(1, int(total_commits * 0.25))
            
            # Estimate after-hours activity
            after_hours_rate = 0.1
            after_hours_commits = int(total_commits * after_hours_rate)
            weekend_rate = 0.05
            weekend_commits = int(total_commits * weekend_rate)
            
            # Burnout indicators
            burnout_indicators = self._calculate_github_burnout_indicators(
                total_commits, commits_per_week
            )
            
            github_activity = {
                'commits_count': total_commits,
                'pull_requests_count': estimated_prs,
                'reviews_count': estimated_reviews,
                'after_hours_commits': after_hours_commits,
                'weekend_commits': weekend_commits,
                'commits_per_week': round(commits_per_week, 2),
                'avg_pr_size': 50,
                'username': github_data.get('username', ''),
                'email': github_data.get('email', ''),
                'burnout_indicators': burnout_indicators,
                'last_updated': datetime.now().isoformat(),
                'data_source': 'top_contributors_fallback'
            }
            
            return github_activity
            
        except Exception as e:
            self.logger.error(f"Error creating GitHub activity from contributor data: {e}")
            return {
                'commits_count': github_data.get('total_commits', 0),
                'pull_requests_count': 0,
                'reviews_count': 0,
                'after_hours_commits': 0,
                'weekend_commits': 0,
                'burnout_indicators': {
                    'excessive_commits': False,
                    'late_night_activity': False,
                    'weekend_work': False,
                    'large_prs': False
                },
                'data_source': 'top_contributors_fallback_basic'
            }
    
    def _calculate_github_burnout_indicators(
        self, 
        total_commits: int, 
        commits_per_week: float
    ) -> Dict[str, bool]:
        """
        Calculate burnout indicators based on GitHub activity patterns
        """
        try:
            # Define thresholds for burnout indicators
            EXCESSIVE_COMMITS_THRESHOLD = 50  # commits per week
            EXCESSIVE_TOTAL_THRESHOLD = 200   # total commits in period
            
            indicators = {
                'excessive_commits': (
                    commits_per_week > EXCESSIVE_COMMITS_THRESHOLD or 
                    total_commits > EXCESSIVE_TOTAL_THRESHOLD
                ),
                'late_night_activity': False,  # Would need timestamp data
                'weekend_work': False,  # Would need timestamp data
                'large_prs': False  # Would need PR size data
            }
            
            return indicators
            
        except Exception as e:
            self.logger.error(f"Error calculating burnout indicators: {e}")
            return {
                'excessive_commits': False,
                'late_night_activity': False,
                'weekend_work': False,
                'large_prs': False
            }
    
    def get_correlation_stats(
        self,
        team_members: List[Dict[str, Any]],
        github_insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get statistics about GitHub data correlation
        """
        try:
            # Count team members with GitHub data
            members_with_github = 0
            total_github_commits = 0
            integration_sourced = 0
            
            for member in team_members:
                if isinstance(member, dict):
                    github_activity = member.get('github_activity', {})
                    # Count any member with a GitHub username (even if 0 commits)
                    if github_activity and github_activity.get('username'):
                        members_with_github += 1
                        total_github_commits += github_activity.get('commits_count', 0)
                        
                        # Count integration-sourced correlations
                        if github_activity.get('data_source') == 'integration_mappings':
                            integration_sourced += 1
            
            # Get available data sources
            top_contributors = github_insights.get('top_contributors', [])
            integration_mappings_count = len(self._fetch_integration_mappings()) if self.current_user_id else 0
            
            stats = {
                'total_team_members': len(team_members),
                'github_contributors_available': len(top_contributors),  # From top_contributors
                'integration_mappings_available': integration_mappings_count,  # From integration_mappings
                'team_members_with_github_data': members_with_github,
                'correlation_rate': (members_with_github / len(team_members)) * 100 if team_members else 0,
                'total_commits_correlated': total_github_commits,
                'avg_commits_per_correlated_member': (
                    total_github_commits / members_with_github if members_with_github > 0 else 0
                ),
                'integration_mappings_used': integration_sourced,
                'improvement_over_top_contributors': max(0, members_with_github - len(top_contributors))
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Error getting correlation stats: {e}")
            return {
                'total_team_members': len(team_members) if team_members else 0,
                'github_contributors_available': 0,
                'integration_mappings_available': 0,
                'team_members_with_github_data': 0,
                'correlation_rate': 0,
                'total_commits_correlated': 0,
                'avg_commits_per_correlated_member': 0,
                'integration_mappings_used': 0,
                'improvement_over_top_contributors': 0
            }