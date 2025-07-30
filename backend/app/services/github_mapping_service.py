"""
Smart GitHub Mapping Service - Enterprise-grade caching and data management.

Separates stable mapping data (email -> username) from dynamic activity data (commits, PRs).
Implements intelligent caching to optimize performance and reduce API calls.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session

from .mapping_recorder import MappingRecorder
from .github_collector import GitHubCollector, collect_team_github_data
from ..models import get_db

logger = logging.getLogger(__name__)


class GitHubMappingService:
    """
    Smart caching service for GitHub mappings vs activity data.
    
    Design Principles:
    - Mapping data (email -> username) is stable: cache for 7 days
    - Activity data (commits, PRs) is dynamic: refresh per analysis
    - Failed mappings: retry every 24 hours
    - Rate limiting: respect GitHub API limits
    """
    
    # Cache TTL policies
    MAPPING_CACHE_DAYS = 7      # Username mappings stable for week
    FAILED_RETRY_HOURS = 24     # Retry failed mappings daily
    ACTIVITY_REFRESH_ALWAYS = True  # Always get fresh activity data
    
    def __init__(self, db: Session = None):
        self.db = db or next(get_db())
        self.recorder = MappingRecorder(self.db)
        self.github_collector = GitHubCollector()
        
    async def get_smart_github_data(
        self, 
        team_emails: List[str], 
        days: int = 30, 
        github_token: str = None,
        user_id: Optional[int] = None,
        analysis_id: Optional[int] = None,
        source_platform: str = "rootly"
    ) -> Dict[str, Dict]:
        """
        Smart GitHub data collection with intelligent caching.
        
        Strategy:
        1. Check for recent successful mappings (reuse if < 7 days old)
        2. For cached mappings: refresh activity data only
        3. For missing/stale mappings: attempt new mapping
        4. For failed mappings: retry if > 24 hours old
        """
        logger.info(f"🧠 SMART CACHING: Processing {len(team_emails)} emails for analysis {analysis_id}")
        
        results = {}
        emails_needing_mapping = []
        emails_needing_activity_refresh = []
        cache_stats = {"hits": 0, "misses": 0, "refreshes": 0, "retries": 0}
        
        # Phase 1: Analyze cache status for each email
        for email in team_emails:
            cached_mapping = self._get_cached_mapping(email, user_id)
            
            if cached_mapping and self._is_mapping_fresh(cached_mapping):
                # Cache HIT: Reuse mapping, refresh activity only
                cache_stats["hits"] += 1
                emails_needing_activity_refresh.append((email, cached_mapping))
                logger.debug(f"📋 Cache HIT: {email} -> {cached_mapping.target_identifier}")
                
            elif cached_mapping and self._is_mapping_stale(cached_mapping):
                # Cache STALE: Mapping old, needs refresh
                cache_stats["refreshes"] += 1
                emails_needing_mapping.append(email)
                logger.debug(f"🔄 Cache STALE: {email} mapping is {self._get_mapping_age_days(cached_mapping)} days old")
                
            elif cached_mapping and not cached_mapping.mapping_successful:
                # Failed mapping: retry if enough time passed
                if self._should_retry_failed_mapping(cached_mapping):
                    cache_stats["retries"] += 1
                    emails_needing_mapping.append(email)
                    logger.debug(f"🔄 RETRY: {email} failed mapping ready for retry")
                else:
                    logger.debug(f"⏳ SKIP: {email} failed mapping too recent to retry")
                    
            else:
                # Cache MISS: No mapping exists
                cache_stats["misses"] += 1
                emails_needing_mapping.append(email)
                logger.debug(f"❌ Cache MISS: {email} no mapping found")
        
        # Phase 2: Refresh activity data for cached mappings
        if emails_needing_activity_refresh:
            logger.info(f"🔄 ACTIVITY REFRESH: Processing {len(emails_needing_activity_refresh)} cached mappings")
            for email, cached_mapping in emails_needing_activity_refresh:
                try:
                    refreshed_data = await self._refresh_activity_data(
                        email, cached_mapping, days, github_token, analysis_id
                    )
                    if refreshed_data:
                        results[email] = refreshed_data
                        # Update mapping record with fresh data points
                        self._update_mapping_data_points(cached_mapping, refreshed_data, analysis_id)
                except Exception as e:
                    logger.warning(f"Failed to refresh activity for {email}: {e}")
                    # Fall back to creating new mapping
                    emails_needing_mapping.append(email)
        
        # Phase 3: Create new mappings for cache misses
        if emails_needing_mapping:
            logger.info(f"🆕 NEW MAPPINGS: Processing {len(emails_needing_mapping)} emails")
            new_results = await self._create_new_mappings(
                emails_needing_mapping, days, github_token, user_id, analysis_id, source_platform
            )
            results.update(new_results)
        
        # Log performance metrics
        total_emails = len(team_emails)
        cache_hit_rate = (cache_stats["hits"] / total_emails) * 100 if total_emails > 0 else 0
        logger.info(f"📊 CACHE PERFORMANCE: {cache_hit_rate:.1f}% hit rate - "
                   f"Hits: {cache_stats['hits']}, Misses: {cache_stats['misses']}, "
                   f"Refreshes: {cache_stats['refreshes']}, Retries: {cache_stats['retries']}")
        
        return results
    
    def _get_cached_mapping(self, email: str, user_id: int) -> Optional[Any]:
        """Get the most recent mapping for an email."""
        from ..models import IntegrationMapping
        return self.db.query(IntegrationMapping).filter(
            IntegrationMapping.user_id == user_id,
            IntegrationMapping.source_identifier == email,
            IntegrationMapping.target_platform == "github"
        ).order_by(IntegrationMapping.created_at.desc()).first()
    
    def _is_mapping_fresh(self, mapping) -> bool:
        """Check if mapping is fresh (successful and < 7 days old)."""
        if not mapping.mapping_successful:
            return False
        age_days = self._get_mapping_age_days(mapping)
        return age_days < self.MAPPING_CACHE_DAYS
    
    def _is_mapping_stale(self, mapping) -> bool:
        """Check if mapping is stale (successful but > 7 days old)."""
        if not mapping.mapping_successful:
            return False
        age_days = self._get_mapping_age_days(mapping)
        return age_days >= self.MAPPING_CACHE_DAYS
    
    def _should_retry_failed_mapping(self, mapping) -> bool:
        """Check if failed mapping should be retried."""
        if mapping.mapping_successful:
            return False
        age_hours = (datetime.utcnow() - mapping.created_at).total_seconds() / 3600
        return age_hours >= self.FAILED_RETRY_HOURS
    
    def _get_mapping_age_days(self, mapping) -> float:
        """Get age of mapping in days."""
        return (datetime.utcnow() - mapping.created_at).total_seconds() / 86400
    
    async def _refresh_activity_data(
        self, 
        email: str, 
        cached_mapping, 
        days: int, 
        github_token: str,
        analysis_id: int
    ) -> Optional[Dict]:
        """
        Refresh activity data for a cached mapping.
        Reuse the username but get fresh commits/PRs/reviews.
        """
        username = cached_mapping.target_identifier
        if not username or username == "unknown":
            return None
            
        logger.debug(f"🔄 Refreshing activity for {email} -> {username}")
        
        try:
            # Get fresh activity data using cached username
            user_data = await self.github_collector.collect_github_data_for_user(
                email, days, github_token
            )
            
            if user_data and isinstance(user_data, dict):
                # Ensure username matches cached mapping
                user_data['username'] = username
                user_data['email'] = email
                return user_data
            else:
                logger.warning(f"No activity data returned for {email} -> {username}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to refresh activity data for {email}: {e}")
            return None
    
    async def _create_new_mappings(
        self,
        emails: List[str],
        days: int,
        github_token: str,
        user_id: int,
        analysis_id: int,
        source_platform: str
    ) -> Dict[str, Dict]:
        """Create new mappings using the enhanced GitHub collector."""
        from .enhanced_github_collector import collect_team_github_data_with_mapping
        
        logger.info(f"🆕 Creating new mappings for {len(emails)} emails")
        
        try:
            return await collect_team_github_data_with_mapping(
                team_emails=emails,
                days=days,
                github_token=github_token,
                user_id=user_id,
                analysis_id=analysis_id,
                source_platform=source_platform
            )
        except Exception as e:
            logger.error(f"Failed to create new mappings: {e}")
            return {}
    
    def _update_mapping_data_points(self, mapping, refreshed_data: Dict, analysis_id: int):
        """Update mapping record with fresh data points count."""
        try:
            if isinstance(refreshed_data, dict):
                metrics = refreshed_data.get("metrics", {})
                data_points = (
                    metrics.get("total_commits", 0) +
                    metrics.get("total_pull_requests", 0) +
                    metrics.get("total_reviews", 0)
                )
                
                # Create new mapping record for this analysis with updated data points
                self.recorder.record_successful_mapping(
                    user_id=mapping.user_id,
                    analysis_id=analysis_id,
                    source_platform=mapping.source_platform,
                    source_identifier=mapping.source_identifier,
                    target_platform="github",
                    target_identifier=mapping.target_identifier,
                    mapping_method="cached_refresh",
                    data_points_count=data_points
                )
                
                logger.debug(f"✅ Updated mapping for {mapping.source_identifier}: {data_points} data points")
                
        except Exception as e:
            logger.warning(f"Failed to update mapping data points: {e}")
    
    def get_cache_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get caching performance statistics."""
        from ..models import IntegrationMapping
        
        # Get recent mappings
        recent_mappings = self.db.query(IntegrationMapping).filter(
            IntegrationMapping.user_id == user_id,
            IntegrationMapping.target_platform == "github",
            IntegrationMapping.created_at >= datetime.utcnow() - timedelta(days=30)
        ).all()
        
        stats = {
            "total_mappings": len(recent_mappings),
            "successful_mappings": len([m for m in recent_mappings if m.mapping_successful]),
            "failed_mappings": len([m for m in recent_mappings if not m.mapping_successful]),
            "fresh_mappings": len([m for m in recent_mappings if self._is_mapping_fresh(m)]),
            "stale_mappings": len([m for m in recent_mappings if self._is_mapping_stale(m)]),
            "average_age_days": sum(self._get_mapping_age_days(m) for m in recent_mappings) / len(recent_mappings) if recent_mappings else 0,
            "cache_efficiency": 0.0
        }
        
        if stats["total_mappings"] > 0:
            stats["cache_efficiency"] = (stats["fresh_mappings"] / stats["total_mappings"]) * 100
        
        return stats