"""
API endpoints for integration mapping data.
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...models import get_db, IntegrationMapping
from ...auth.dependencies import get_current_active_user
from ...models.user import User
from ...services.mapping_recorder import MappingRecorder

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/mappings", summary="Get user's integration mappings")
async def get_user_mappings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get all integration mappings for the current user."""
    try:
        recorder = MappingRecorder(db)
        mappings = recorder.get_user_mappings(current_user.id)
        return [mapping.to_dict() for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching user mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mappings")

@router.get("/mappings/recent", summary="Get recent integration mappings")
async def get_recent_mappings(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get recent integration mappings for the current user."""
    try:
        recorder = MappingRecorder(db)
        mappings = recorder.get_recent_mappings(current_user.id, limit)
        return [mapping.to_dict() for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching recent mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent mappings")

@router.get("/mappings/statistics", summary="Get mapping statistics")
async def get_mapping_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get mapping statistics for the current user."""
    try:
        recorder = MappingRecorder(db)
        stats = recorder.get_mapping_statistics(current_user.id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching mapping statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch mapping statistics")

@router.get("/mappings/analysis/{analysis_id}", summary="Get mappings for specific analysis")
async def get_analysis_mappings(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get all integration mappings for a specific analysis with proper team member statistics."""
    try:
        # Verify the analysis belongs to the current user
        from ...models import Analysis
        analysis = db.query(Analysis).filter(
            Analysis.id == analysis_id,
            Analysis.user_id == current_user.id
        ).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail="Analysis not found")
        
        recorder = MappingRecorder(db)
        mappings = recorder.get_analysis_mappings(analysis_id)
        
        # Calculate proper team member statistics
        github_mappings = [m for m in mappings if m.target_platform == "github"]
        
        # Get unique team members (by email)
        unique_emails = set(m.source_identifier for m in github_mappings)
        total_team_members = len(unique_emails)
        
        # Count successful mappings (unique emails with successful mapping)
        successful_emails = set()
        members_with_data = 0
        
        for mapping in github_mappings:
            if mapping.mapping_successful and mapping.target_identifier != "unknown":
                successful_emails.add(mapping.source_identifier)
                if mapping.data_points_count and mapping.data_points_count > 0:
                    members_with_data += 1
        
        successful_mappings = len(successful_emails)
        
        # Calculate proper success rate based on team members, not API calls
        success_rate = (successful_mappings / total_team_members * 100) if total_team_members > 0 else 0
        
        return {
            "mappings": [mapping.to_dict() for mapping in mappings],
            "statistics": {
                "total_team_members": total_team_members,
                "successful_mappings": successful_mappings,
                "members_with_data": members_with_data,
                "success_rate": round(success_rate, 1),
                "failed_mappings": total_team_members - successful_mappings
            },
            "analysis_id": analysis_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching analysis mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analysis mappings")

@router.get("/mappings/platform/{platform}", summary="Get mappings for specific platform")
async def get_platform_mappings(
    platform: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> List[dict]:
    """Get all integration mappings for a specific target platform."""
    try:
        mappings = db.query(IntegrationMapping).filter(
            IntegrationMapping.user_id == current_user.id,
            IntegrationMapping.target_platform == platform
        ).order_by(IntegrationMapping.created_at.desc()).all()
        
        return [mapping.to_dict() for mapping in mappings]
    except Exception as e:
        logger.error(f"Error fetching platform mappings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch platform mappings")

@router.get("/mappings/success-rate", summary="Get success rates by platform")
async def get_success_rates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get success rates broken down by platform combinations."""
    try:
        recorder = MappingRecorder(db)
        stats = recorder.get_mapping_statistics(current_user.id)
        
        # Extract just the platform stats for easier consumption
        platform_success_rates = {}
        for platform_combo, stats_data in stats.get("platform_stats", {}).items():
            platform_success_rates[platform_combo] = {
                "total_attempts": stats_data["total"],
                "successful": stats_data["successful"],
                "failed": stats_data["failed"],
                "success_rate": round(stats_data["success_rate"] * 100, 1)  # Convert to percentage
            }
        
        return {
            "overall_success_rate": round(stats.get("success_rate", 0) * 100, 1),
            "total_attempts": stats.get("total_attempts", 0),
            "platform_breakdown": platform_success_rates
        }
    except Exception as e:
        logger.error(f"Error fetching success rates: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch success rates")

@router.get("/mappings/github/health", summary="Get GitHub API health and performance metrics")
async def get_github_api_health(
    current_user: User = Depends(get_current_active_user)
) -> dict:
    """Get GitHub API manager health status and performance metrics."""
    try:
        from ...services.github_api_manager import github_api_manager
        health_status = github_api_manager.get_health_status()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "github_api_health": health_status,
            "recommendations": _generate_health_recommendations(health_status)
        }
    except Exception as e:
        logger.error(f"Error fetching GitHub API health: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch GitHub API health")

@router.get("/mappings/github/cache-stats", summary="Get GitHub mapping cache statistics")
async def get_github_cache_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """Get GitHub mapping cache performance statistics."""
    try:
        from ...services.github_mapping_service import GitHubMappingService
        mapping_service = GitHubMappingService(db)
        cache_stats = mapping_service.get_cache_statistics(current_user.id)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "cache_statistics": cache_stats,
            "performance_insights": _generate_cache_insights(cache_stats)
        }
    except Exception as e:
        logger.error(f"Error fetching cache statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cache statistics")

def _generate_health_recommendations(health_status: dict) -> List[str]:
    """Generate actionable recommendations based on GitHub API health."""
    recommendations = []
    
    rate_limit = health_status.get("rate_limit_usage", {})
    performance = health_status.get("performance_metrics", {})
    circuit_state = health_status.get("circuit_breaker_state")
    
    # Rate limit recommendations
    usage_pct = rate_limit.get("usage_percentage", 0)
    if usage_pct > 90:
        recommendations.append("🚨 Rate limit usage is very high (>90%). Consider implementing request batching.")
    elif usage_pct > 70:
        recommendations.append("⚠️ Rate limit usage is elevated (>70%). Monitor usage closely.")
    
    # Circuit breaker recommendations
    if circuit_state == "open":
        recommendations.append("🔴 Circuit breaker is OPEN. GitHub API calls are being blocked due to failures.")
    elif circuit_state == "half_open":
        recommendations.append("🟡 Circuit breaker is HALF_OPEN. System is attempting recovery.")
    
    # Performance recommendations
    success_rate = performance.get("success_rate", 0)
    if success_rate < 90:
        recommendations.append(f"📉 Success rate is below 90% ({success_rate:.1f}%). Check API token and permissions.")
    
    avg_response = performance.get("average_response_time", 0)
    if avg_response > 5:
        recommendations.append(f"⏱️ Average response time is high ({avg_response:.2f}s). Consider request optimization.")
    
    if not recommendations:
        recommendations.append("✅ GitHub API health is good. No immediate action required.")
    
    return recommendations

def _generate_cache_insights(cache_stats: dict) -> List[str]:
    """Generate insights based on cache performance."""
    insights = []
    
    cache_efficiency = cache_stats.get("cache_efficiency", 0)
    total_mappings = cache_stats.get("total_mappings", 0)
    
    if cache_efficiency > 80:
        insights.append(f"🚀 Excellent cache efficiency ({cache_efficiency:.1f}%). Most mappings are being reused.")
    elif cache_efficiency > 60:
        insights.append(f"✅ Good cache efficiency ({cache_efficiency:.1f}%). Room for minor optimization.")
    elif cache_efficiency > 40:
        insights.append(f"⚠️ Moderate cache efficiency ({cache_efficiency:.1f}%). Consider reviewing mapping TTL policies.")
    else:
        insights.append(f"🔴 Low cache efficiency ({cache_efficiency:.1f}%). Many mappings are being recreated.")
    
    if total_mappings == 0:
        insights.append("ℹ️ No mapping data available yet. Cache statistics will improve after running analyses.")
    
    fresh_mappings = cache_stats.get("fresh_mappings", 0)
    stale_mappings = cache_stats.get("stale_mappings", 0)
    
    if stale_mappings > fresh_mappings:
        insights.append("🧹 Many stale mappings detected. Cache cleanup may improve performance.")
    
    return insights

@router.post("/mappings/github/cleanup-duplicates", summary="Clean up duplicate GitHub mappings")
async def cleanup_duplicate_github_mappings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> dict:
    """
    Clean up duplicate GitHub mappings, keeping only the most recent for each user-email.
    This removes stale data from before Phase 1 fixes.
    """
    try:
        from sqlalchemy import text
        
        logger.info(f"🧹 Starting duplicate cleanup for user {current_user.id}")
        
        # Get duplicates for this user
        query = text("""
        SELECT source_identifier, COUNT(*) as duplicate_count,
               array_agg(id ORDER BY created_at DESC) as mapping_ids,
               array_agg(target_identifier ORDER BY created_at DESC) as usernames,
               array_agg(mapping_successful ORDER BY created_at DESC) as success_flags
        FROM integration_mappings 
        WHERE target_platform = 'github' AND user_id = :user_id
        GROUP BY source_identifier 
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        """)
        
        duplicates = db.execute(query, {"user_id": current_user.id}).fetchall()
        
        if not duplicates:
            return {
                "message": "✅ No duplicate mappings found for your account",
                "duplicates_found": 0,
                "duplicates_removed": 0,
                "emails_processed": 0
            }
        
        total_deleted = 0
        emails_processed = len(duplicates)
        
        for row in duplicates:
            email = row[0]
            duplicate_count = row[1]
            mapping_ids = row[2]  # Already sorted DESC by created_at
            usernames = row[3]
            success_flags = row[4]
            
            # Keep the most recent (first), delete the rest
            keep_id = mapping_ids[0]
            delete_ids = mapping_ids[1:]
            
            logger.info(f"📧 {email}: Keeping ID {keep_id} -> {usernames[0]}, deleting {len(delete_ids)} older mappings")
            
            # Delete older mappings
            delete_query = text("DELETE FROM integration_mappings WHERE id = ANY(:ids)")
            result = db.execute(delete_query, {"ids": delete_ids})
            deleted_count = result.rowcount
            total_deleted += deleted_count
        
        # Commit all deletions
        db.commit()
        
        logger.info(f"🎉 Cleanup complete: {emails_processed} emails processed, {total_deleted} duplicates removed")
        
        return {
            "message": f"🎉 Successfully cleaned up duplicate mappings!",
            "duplicates_found": sum(row[1] - 1 for row in duplicates),  # Total duplicates (excluding kept ones)
            "duplicates_removed": total_deleted,
            "emails_processed": emails_processed,
            "next_steps": [
                "Run a new burnout analysis with GitHub integration",
                "Check GitHub Data Mapping modal",
                "Verify each team member appears only once"
            ]
        }
        
    except Exception as e:
        logger.error(f"❌ Cleanup failed for user {current_user.id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")