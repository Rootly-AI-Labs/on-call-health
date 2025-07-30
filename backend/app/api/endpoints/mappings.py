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
) -> List[dict]:
    """Get all integration mappings for a specific analysis."""
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
        return [mapping.to_dict() for mapping in mappings]
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