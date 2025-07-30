"""
Burnout analysis API endpoints.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...models import get_db, User, Analysis, RootlyIntegration, SlackIntegration, GitHubIntegration
from ...auth.dependencies import get_current_active_user
from ...services.burnout_analyzer import BurnoutAnalyzerService
from ...services.pagerduty_burnout_analyzer import PagerDutyBurnoutAnalyzerService
from ...services.unified_burnout_analyzer import UnifiedBurnoutAnalyzer

logger = logging.getLogger(__name__)

router = APIRouter()


class RunAnalysisRequest(BaseModel):
    integration_id: int
    time_range: int = 30  # days
    include_weekends: bool = True
    include_github: bool = False
    include_slack: bool = False
    enable_ai: bool = False


class AnalysisResponse(BaseModel):
    id: int
    uuid: Optional[str]
    integration_id: Optional[int]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    time_range: int
    analysis_data: Optional[dict]


class AnalysisListResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total: int


class DailyTrendPoint(BaseModel):
    date: str
    overall_score: float
    average_burnout_score: float
    members_at_risk: int
    total_members: int
    health_status: str
    analysis_count: int  # Number of analyses that day


class TimelineEvent(BaseModel):
    date: str
    iso_date: str
    status: str
    title: str
    description: str
    color: str
    impact: str  # 'positive', 'negative', 'neutral'
    severity: str  # 'low', 'medium', 'high', 'critical'
    metrics: Dict[str, Any]


class HistoricalTrendsResponse(BaseModel):
    daily_trends: List[DailyTrendPoint]
    timeline_events: List[TimelineEvent]
    summary: Dict[str, Any]
    date_range: Dict[str, str]


@router.post("/run", response_model=AnalysisResponse)
async def run_burnout_analysis(
    request: RunAnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Run a new burnout analysis for a specific integration and time range."""
    print(f"ENDPOINT_DEBUG: Entered run_burnout_analysis for integration {request.integration_id}")
    print(f"ENDPOINT_DEBUG: Request params - include_github: {request.include_github}, include_slack: {request.include_slack}")
    logger.info(f"ENDPOINT_DEBUG: Entered run_burnout_analysis for integration {request.integration_id}")
    logger.info(f"ENDPOINT_DEBUG: Request params - include_github: {request.include_github}, include_slack: {request.include_slack}")
    # Verify the integration belongs to the current user
    integration = db.query(RootlyIntegration).filter(
        RootlyIntegration.id == request.integration_id,
        RootlyIntegration.user_id == current_user.id,
        RootlyIntegration.is_active == True
    ).first()
    
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Integration not found or not active"
        )
    
    # Create new analysis record
    analysis = Analysis(
        user_id=current_user.id,
        rootly_integration_id=integration.id,
        time_range=request.time_range,
        status="pending",
        config={
            "include_weekends": request.include_weekends,
            "include_github": request.include_github,
            "include_slack": request.include_slack
        }
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    # Update integration last_used_at
    integration.last_used_at = datetime.now()
    db.commit()
    
    # Start analysis in background
    logger.info(f"ENDPOINT: About to add background task for analysis {analysis.id}")
    try:
        background_tasks.add_task(
            run_analysis_task,
            analysis_id=analysis.id,
            integration_id=integration.id,
            api_token=integration.api_token,
            platform=integration.platform,
            time_range=request.time_range,
            include_weekends=request.include_weekends,
            include_github=request.include_github,
            include_slack=request.include_slack,
            user_id=current_user.id,
            enable_ai=request.enable_ai
        )
        logger.info(f"ENDPOINT: Successfully added background task for analysis {analysis.id}")
    except Exception as e:
        logger.error(f"ENDPOINT: Failed to add background task for analysis {analysis.id}: {e}")
        raise
    
    return AnalysisResponse(
        id=analysis.id,
        uuid=getattr(analysis, 'uuid', None),
        integration_id=analysis.rootly_integration_id,
        status=analysis.status,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        time_range=analysis.time_range,
        analysis_data=None
    )


@router.get("", response_model=AnalysisListResponse)
async def list_analyses(
    integration_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all previous analyses for the current user."""
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)
    
    # Filter by integration if specified
    if integration_id:
        # Verify the integration belongs to the user
        integration = db.query(RootlyIntegration).filter(
            RootlyIntegration.id == integration_id,
            RootlyIntegration.user_id == current_user.id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        query = query.filter(Analysis.rootly_integration_id == integration_id)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    analyses = query.order_by(Analysis.created_at.desc()).offset(offset).limit(limit).all()
    
    # Convert to response format
    response_analyses = []
    for analysis in analyses:
        response_analyses.append(
            AnalysisResponse(
                id=analysis.id,
                uuid=getattr(analysis, 'uuid', None),
                integration_id=analysis.rootly_integration_id,
                status=analysis.status,
                created_at=analysis.created_at,
                completed_at=analysis.completed_at,
                time_range=analysis.time_range or 30,
                analysis_data=analysis.results
            )
        )
    
    return AnalysisListResponse(
        analyses=response_analyses,
        total=total
    )


@router.get("/uuid/{analysis_uuid}", response_model=AnalysisResponse)
async def get_analysis_by_uuid(
    analysis_uuid: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific analysis result by UUID."""
    try:
        analysis = db.query(Analysis).filter(
            Analysis.uuid == analysis_uuid,
            Analysis.user_id == current_user.id
        ).first()
    except Exception:
        # UUID column doesn't exist yet
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="UUID lookup not available until migration is complete"
        )
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return AnalysisResponse(
        id=analysis.id,
        uuid=getattr(analysis, 'uuid', None),
        integration_id=analysis.rootly_integration_id,
        status=analysis.status,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        time_range=analysis.time_range or 30,
        analysis_data=analysis.results
    )


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get a specific analysis result."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    return AnalysisResponse(
        id=analysis.id,
        uuid=getattr(analysis, 'uuid', None),
        integration_id=analysis.rootly_integration_id,
        status=analysis.status,
        created_at=analysis.created_at,
        completed_at=analysis.completed_at,
        time_range=analysis.time_range or 30,
        analysis_data=analysis.results
    )


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete a specific analysis."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    # Delete the analysis
    db.delete(analysis)
    db.commit()
    
    logger.info(f"Analysis {analysis_id} deleted by user {current_user.id}")
    
    return {"message": "Analysis deleted successfully"}


@router.get("/trends/historical", response_model=HistoricalTrendsResponse)
async def get_historical_trends(
    integration_id: Optional[int] = None,
    days_back: int = 14,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get daily incident trends from the most recent analysis period."""
    
    # Find the most recent completed analysis
    query = db.query(Analysis).filter(
        Analysis.user_id == current_user.id,
        Analysis.status == "completed",
        Analysis.results.isnot(None)
    )
    
    # Filter by integration if specified
    if integration_id:
        # Verify the integration belongs to the user
        integration = db.query(RootlyIntegration).filter(
            RootlyIntegration.id == integration_id,
            RootlyIntegration.user_id == current_user.id
        ).first()
        
        if not integration:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Integration not found"
            )
        
        query = query.filter(Analysis.rootly_integration_id == integration_id)
    
    # Get the most recent analysis
    analysis = query.order_by(Analysis.created_at.desc()).first()
    
    if not analysis:
        # Return empty trends if no analysis found
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return HistoricalTrendsResponse(
            daily_trends=[],
            timeline_events=[],
            summary={
                "total_analyses": 0,
                "days_with_data": 0,
                "trend_direction": "insufficient_data",
                "average_score": 0.0
            },
            date_range={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
    
    # Extract daily trends from the analysis results
    results = analysis.results
    if not results or not isinstance(results, dict):
        # Fallback to empty response
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        return HistoricalTrendsResponse(
            daily_trends=[],
            timeline_events=[],
            summary={
                "total_analyses": 1,
                "days_with_data": 0,
                "trend_direction": "insufficient_data",
                "average_score": 0.0
            },
            date_range={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
    
    # Get daily trends from analysis results
    analysis_daily_trends = results.get("daily_trends", [])
    if not analysis_daily_trends or not isinstance(analysis_daily_trends, list):
        # Fallback to empty response
        metadata = results.get("metadata", {})
        days_analyzed = metadata.get("days_analyzed", days_back)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_analyzed)
        return HistoricalTrendsResponse(
            daily_trends=[],
            timeline_events=[],
            summary={
                "total_analyses": 1,
                "days_with_data": 0,
                "trend_direction": "insufficient_data",
                "average_score": 0.0
            },
            date_range={
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d")
            }
        )
    
    # Convert analysis daily trends to API format and filter by days_back if needed
    daily_trends = []
    all_scores = []
    
    # Calculate cutoff date for filtering
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    for trend_data in analysis_daily_trends:
        if not isinstance(trend_data, dict):
            continue
            
        trend_date = trend_data.get("date")
        if not trend_date:
            continue
            
        # Filter by date range if specified
        try:
            trend_datetime = datetime.strptime(trend_date, "%Y-%m-%d")
            if trend_datetime < start_date:
                continue
        except (ValueError, TypeError):
            continue
        
        # Get incident count to determine members at risk
        incident_count = trend_data.get("incident_count", 0)
        users_involved_count = trend_data.get("users_involved_count", 0)
        
        # Estimate members at risk based on incident patterns
        members_at_risk = 0
        if incident_count > 0:
            if incident_count >= 5:  # High incident volume
                members_at_risk = min(users_involved_count + 1, 5)
            elif incident_count >= 3:  # Medium incident volume
                members_at_risk = min(users_involved_count, 3)
            elif users_involved_count > 0:  # Low volume but someone involved
                members_at_risk = users_involved_count
        
        # Get health status based on score
        overall_score = trend_data.get("overall_score", 0.0)
        if overall_score <= 4.0:
            health_status = "critical"
        elif overall_score <= 6.5:
            health_status = "at_risk" 
        elif overall_score <= 8.0:
            health_status = "moderate"
        else:
            health_status = "healthy"
        
        daily_trends.append(DailyTrendPoint(
            date=trend_date,
            overall_score=float(overall_score),
            average_burnout_score=float(trend_data.get("overall_score", 0.0)),  # Use same score for consistency
            members_at_risk=int(members_at_risk),
            total_members=max(int(users_involved_count), 1),  # At least 1 to avoid division by zero
            health_status=health_status,
            analysis_count=1  # Single analysis
        ))
        
        all_scores.append(overall_score)
    
    # Calculate trend summary
    trend_direction = "stable"
    if len(all_scores) >= 2:
        score_change = all_scores[-1] - all_scores[0]
        if score_change > 0.5:
            trend_direction = "improving"
        elif score_change < -0.5:
            trend_direction = "declining"
    
    summary = {
        "total_analyses": 1,  # Single analysis
        "days_with_data": len(daily_trends),
        "trend_direction": trend_direction,
        "average_score": round(sum(all_scores) / len(all_scores) if all_scores else 0.0, 2),
        "score_change": round(all_scores[-1] - all_scores[0] if len(all_scores) >= 2 else 0.0, 2),
        "best_day": max(daily_trends, key=lambda x: x.overall_score).date if daily_trends else None,
        "worst_day": min(daily_trends, key=lambda x: x.overall_score).date if daily_trends else None
    }
    
    # Get date range from the analysis metadata or daily trends
    metadata = results.get("metadata", {})
    days_analyzed = metadata.get("days_analyzed", days_back)
    
    if daily_trends:
        # Use actual date range from trends
        start_date_str = min(trend.date for trend in daily_trends)
        end_date_str = max(trend.date for trend in daily_trends)
    else:
        # Use calculated date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_analyzed)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
    
    # Generate timeline events from historical analysis data
    timeline_events = []
    
    if daily_trends:
        # Analyze patterns and create meaningful timeline events
        for i, trend in enumerate(daily_trends):
            events_for_day = []
            
            # Score-based events (for different risk levels)
            if trend.overall_score <= 4.0:  # Critical burnout period
                events_for_day.append({
                    "status": "critical-burnout", 
                    "title": "Critical Burnout Period",
                    "description": f"Team health dropped to {round(trend.overall_score * 10)}%. {trend.members_at_risk} members at high risk.",
                    "color": "bg-red-600",
                    "impact": "negative",
                    "severity": "critical",
                    "metrics": {"health_score": trend.overall_score, "at_risk_count": trend.members_at_risk}
                })
            elif trend.overall_score <= 6.5 or trend.members_at_risk >= 3:  # Medium risk period  
                # Show medium risk if health is low OR if many members are at risk
                risk_reason = []
                if trend.overall_score <= 6.5:
                    risk_reason.append(f"health at {round(trend.overall_score * 10)}%")
                if trend.members_at_risk >= 3:
                    risk_reason.append(f"{round(trend.members_at_risk)} members at risk")
                
                events_for_day.append({
                    "status": "medium-risk", 
                    "title": "Medium Burnout Risk",
                    "description": f"Team showing warning signs: {' and '.join(risk_reason)}. Monitoring recommended.",
                    "color": "bg-orange-500",
                    "impact": "negative",
                    "severity": "medium",
                    "metrics": {"health_score": trend.overall_score, "at_risk_count": trend.members_at_risk}
                })
            # High performance tracking (only for sustained excellence)
            if trend.overall_score >= 9.0 and trend.members_at_risk == 0:
                # Check if this is sustained excellence (not first day)
                if i > 0:
                    prev_trend = daily_trends[i-1]
                    if prev_trend.overall_score >= 8.5:  # Was already high
                        events_for_day.append({
                            "status": "excellence",
                            "title": "Sustained Excellence",
                            "description": f"Team maintains excellent health at {round(trend.overall_score * 10)}%. Zero members at risk.",
                            "color": "bg-emerald-500",
                            "impact": "positive",
                            "severity": "low",
                            "metrics": {"health_score": trend.overall_score, "sustained": True}
                        })
            
            # Compare with previous day for trend events
            if i > 0:
                prev_trend = daily_trends[i-1]
                score_change = trend.overall_score - prev_trend.overall_score
                
                if score_change >= 1.0:  # Significant improvement
                    # Determine if this is recovery (from low scores) or just improvement
                    if prev_trend.overall_score <= 6.0 and trend.overall_score >= 7.5:
                        # True recovery: moving from poor/fair to good health
                        events_for_day.append({
                            "status": "recovery",
                            "title": "Recovery Period",
                            "description": f"Health recovered from {round(prev_trend.overall_score * 10)}% to {round(trend.overall_score * 10)}%. Team moving out of burnout risk.",
                            "color": "bg-green-500",
                            "impact": "positive",
                            "severity": "low",
                            "metrics": {"score_change": score_change, "previous_score": prev_trend.overall_score, "recovery": True}
                        })
                    else:
                        # Regular improvement
                        events_for_day.append({
                            "status": "improvement",
                            "title": "Health Improvement",
                            "description": f"Health score increased by {round(score_change * 10)} points from {round(prev_trend.overall_score * 10)}%.",
                            "color": "bg-blue-500",
                            "impact": "positive",
                            "severity": "low",
                            "metrics": {"score_change": score_change, "previous_score": prev_trend.overall_score}
                        })
                elif score_change <= -1.0:  # Significant decline
                    events_for_day.append({
                        "status": "decline",
                        "title": "Health Decline",
                        "description": f"Health score dropped by {round(abs(score_change) * 10)} points. Increased workload stress.",
                        "color": "bg-orange-500",
                        "impact": "negative",
                        "severity": "medium",
                        "metrics": {"score_change": score_change, "previous_score": prev_trend.overall_score}
                    })
                
                # Members at risk changes (more meaningful thresholds)
                risk_change = trend.members_at_risk - prev_trend.members_at_risk
                if risk_change >= 2:  # Significant increase in at-risk members
                    events_for_day.append({
                        "status": "risk-increase",
                        "title": "Rising Burnout Risk",
                        "description": f"{round(risk_change)} additional team members moved to high-risk category ({prev_trend.members_at_risk:.0f} → {trend.members_at_risk:.0f}).",
                        "color": "bg-red-500",
                        "impact": "negative",
                        "severity": "high",
                        "metrics": {"risk_increase": risk_change, "total_at_risk": trend.members_at_risk}
                    })
                elif risk_change <= -2:  # Significant decrease in at-risk members
                    events_for_day.append({
                        "status": "risk-decrease",
                        "title": "Risk Reduction Success",
                        "description": f"{round(abs(risk_change))} team members moved out of high-risk category ({prev_trend.members_at_risk:.0f} → {trend.members_at_risk:.0f}).",
                        "color": "bg-green-400",
                        "impact": "positive",
                        "severity": "low",
                        "metrics": {"risk_decrease": abs(risk_change), "total_at_risk": trend.members_at_risk}
                    })
                elif trend.members_at_risk == 0 and prev_trend.members_at_risk > 0:  # All risk eliminated
                    events_for_day.append({
                        "status": "risk-eliminated",
                        "title": "All Risk Eliminated",
                        "description": f"All {round(prev_trend.members_at_risk)} at-risk team members have recovered. Zero burnout risk achieved.",
                        "color": "bg-green-500",
                        "impact": "positive",
                        "severity": "low",
                        "metrics": {"risk_eliminated": prev_trend.members_at_risk, "total_at_risk": 0}
                    })
            
            # Add events for this day to timeline
            for event_data in events_for_day:
                timeline_events.append(TimelineEvent(
                    date=trend.date,
                    iso_date=trend.date,  # Already in YYYY-MM-DD format
                    status=event_data["status"],
                    title=event_data["title"],
                    description=event_data["description"],
                    color=event_data["color"],
                    impact=event_data["impact"],
                    severity=event_data["severity"],
                    metrics=event_data["metrics"]
                ))
        
        # Add current status event if we have recent data
        if daily_trends:
            latest_trend = daily_trends[-1]
            timeline_events.append(TimelineEvent(
                date=latest_trend.date,
                iso_date=latest_trend.date,
                status="current",
                title="Current Status",
                description=f"Current health: {round(latest_trend.overall_score * 10)}%. {latest_trend.members_at_risk} members need attention.",
                color="bg-purple-500",
                impact="neutral",
                severity="medium" if latest_trend.members_at_risk > 0 else "low",
                metrics={
                    "current_score": latest_trend.overall_score,
                    "members_at_risk": latest_trend.members_at_risk,
                    "total_members": latest_trend.total_members
                }
            ))
    
    return HistoricalTrendsResponse(
        daily_trends=daily_trends,
        timeline_events=timeline_events,
        summary=summary,
        date_range={
            "start_date": start_date_str,
            "end_date": end_date_str
        }
    )


class DailyIncidentTrendPoint(BaseModel):
    date: str
    overall_score: float
    incident_count: int
    severity_weighted_count: float
    after_hours_count: int
    high_severity_count: int
    users_involved: int
    members_at_risk: int
    total_members: int
    health_status: str
    health_percentage: float


class DailyIncidentTrendsResponse(BaseModel):
    daily_trends: List[DailyIncidentTrendPoint]
    summary: Dict[str, Any]
    metadata: Dict[str, Any]


@router.get("/{analysis_id}/daily-trends", response_model=DailyIncidentTrendsResponse)
async def get_analysis_daily_trends(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get daily incident trends from a specific analysis."""
    
    # Get the analysis
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    if analysis.status != "completed" or not analysis.results:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis is not completed or has no results"
        )
    
    results = analysis.results
    daily_trends_data = results.get("daily_trends", [])
    
    if not daily_trends_data:
        # Return empty trends if no daily data available
        return DailyIncidentTrendsResponse(
            daily_trends=[],
            summary={
                "total_days": 0,
                "days_with_incidents": 0,
                "avg_daily_score": 0.0,
                "trend_direction": "insufficient_data"
            },
            metadata={
                "analysis_id": analysis_id,
                "time_range": analysis.time_range or 30,
                "data_source": "current_analysis_daily_trends",
                "generated_at": datetime.now().isoformat()
            }
        )
    
    # Convert to response format
    daily_trends = []
    for trend in daily_trends_data:
        daily_trends.append(DailyIncidentTrendPoint(
            date=trend["date"],
            overall_score=trend["overall_score"],
            incident_count=trend["incident_count"],
            severity_weighted_count=trend.get("severity_weighted_count", 0.0),
            after_hours_count=trend.get("after_hours_count", 0),
            high_severity_count=trend.get("high_severity_count", 0),
            users_involved=trend.get("users_involved", 0),
            members_at_risk=trend.get("members_at_risk", 0),
            total_members=trend.get("total_members", 0),
            health_status=trend.get("health_status", "unknown"),
            health_percentage=trend.get("health_percentage", trend["overall_score"] * 10)
        ))
    
    # Calculate summary statistics
    if daily_trends:
        scores = [t.overall_score for t in daily_trends]
        avg_score = sum(scores) / len(scores)
        
        # Determine trend direction
        trend_direction = "stable"
        if len(scores) >= 2:
            score_change = scores[-1] - scores[0]
            if score_change > 0.5:
                trend_direction = "improving"
            elif score_change < -0.5:
                trend_direction = "declining"
        
        summary = {
            "total_days": len(daily_trends),
            "days_with_incidents": len([t for t in daily_trends if t.incident_count > 0]),
            "avg_daily_score": round(avg_score, 2),
            "trend_direction": trend_direction,
            "score_range": {
                "min": round(min(scores), 2),
                "max": round(max(scores), 2)
            },
            "total_incidents": sum(t.incident_count for t in daily_trends),
            "total_after_hours": sum(t.after_hours_count for t in daily_trends),
            "peak_incident_day": max(daily_trends, key=lambda x: x.incident_count).date if daily_trends else None
        }
    else:
        summary = {
            "total_days": 0,
            "days_with_incidents": 0,
            "avg_daily_score": 0.0,
            "trend_direction": "insufficient_data"
        }
    
    return DailyIncidentTrendsResponse(
        daily_trends=daily_trends,
        summary=summary,
        metadata={
            "analysis_id": analysis_id,
            "time_range": analysis.time_range or 30,
            "data_source": "current_analysis_daily_trends",
            "generated_at": datetime.now().isoformat()
        }
    )


async def run_analysis_task(
    analysis_id: int,
    integration_id: int,
    api_token: str,
    platform: str,
    time_range: int,
    include_weekends: bool,
    include_github: bool = False,
    include_slack: bool = False,
    user_id: int = None,
    enable_ai: bool = False
):
    """Background task to run the actual burnout analysis."""
    import asyncio
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"BACKGROUND_TASK: Starting analysis {analysis_id} with timeout mechanism")
    logger.info(f"BACKGROUND_TASK: GitHub/Slack params - include_github: {include_github}, include_slack: {include_slack}")
    logger.info(f"BACKGROUND_TASK: User ID received: {user_id}")
    logger.info(f"BACKGROUND_TASK: AI params - enable_ai: {enable_ai}")
    print(f"BACKGROUND_TASK: GitHub/Slack params - include_github: {include_github}, include_slack: {include_slack}")
    print(f"BACKGROUND_TASK: User ID received: {user_id}")
    print(f"BACKGROUND_TASK: AI params - enable_ai: {enable_ai}")
    
    db = next(get_db())
    
    try:
        # Update status to running
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            logger.info(f"BACKGROUND_TASK: Analysis {analysis_id} not found in database")
            return  # Analysis doesn't exist
            
        logger.info(f"BACKGROUND_TASK: Setting analysis {analysis_id} to running status")
        analysis.status = "running"
        db.commit()
        
        # Fetch user-specific integration tokens if needed
        slack_token = None
        github_token = None
        
        logger.info(f"BACKGROUND_TASK: Checking conditions - user_id: {user_id}, include_slack: {include_slack}, include_github: {include_github}")
        
        if user_id and (include_slack or include_github):
            logger.info(f"BACKGROUND_TASK: Fetching user {user_id} integrations for analysis {analysis_id}")
            
            if include_slack:
                logger.info(f"BACKGROUND_TASK: Looking for Slack integration for user {user_id}")
                slack_integration = db.query(SlackIntegration).filter(
                    SlackIntegration.user_id == user_id
                ).first()
                logger.info(f"BACKGROUND_TASK: Slack integration query result: {slack_integration}")
                if slack_integration and slack_integration.slack_token:
                    # Decrypt the token
                    from ...api.endpoints.slack import decrypt_token
                    slack_token = decrypt_token(slack_integration.slack_token)
                    logger.info(f"BACKGROUND_TASK: Found Slack integration for user {user_id} with token: {slack_token[:10]}...")
                else:
                    logger.warning(f"BACKGROUND_TASK: No Slack integration found for user {user_id}")
            
            if include_github:
                logger.info(f"BACKGROUND_TASK: Looking for GitHub integration for user {user_id}")
                github_integration = db.query(GitHubIntegration).filter(
                    GitHubIntegration.user_id == user_id
                ).first()
                logger.info(f"BACKGROUND_TASK: GitHub integration query result: {github_integration}")
                if github_integration and github_integration.github_token:
                    # Decrypt the token
                    from ...api.endpoints.github import decrypt_token as decrypt_github_token
                    github_token = decrypt_github_token(github_integration.github_token)
                    logger.info(f"BACKGROUND_TASK: Found GitHub integration for user {user_id} with token: {github_token[:10]}...")
                else:
                    logger.warning(f"BACKGROUND_TASK: No GitHub integration found for user {user_id}")
        else:
            logger.info(f"BACKGROUND_TASK: Skipping user integrations - user_id: {user_id}, include_slack: {include_slack}, include_github: {include_github}")

        # Initialize analyzer service based on platform and AI enablement
        logger.info(f"BACKGROUND_TASK: Initializing {platform} analyzer service for analysis {analysis_id}, enable_ai: {enable_ai}")
        
        # Check if user has LLM token and AI is enabled
        use_ai_analyzer = False
        logger.info(f"BACKGROUND_TASK: Checking AI analyzer conditions - enable_ai: {enable_ai}, user_id: {user_id}")
        print(f"BACKGROUND_TASK: Checking AI analyzer conditions - enable_ai: {enable_ai}, user_id: {user_id}")
        
        if enable_ai and user_id:
            user = db.query(User).filter(User.id == user_id).first()
            logger.info(f"BACKGROUND_TASK: User query result - user exists: {user is not None}")
            print(f"BACKGROUND_TASK: User query result - user exists: {user is not None}")
            
            if user:
                logger.info(f"BACKGROUND_TASK: User details - has_llm_token: {user.llm_token is not None}, provider: {user.llm_provider}")
                print(f"BACKGROUND_TASK: User details - has_llm_token: {user.llm_token is not None}, provider: {user.llm_provider}")
                
            if user and user.llm_token and user.llm_provider:
                use_ai_analyzer = True
                logger.info(f"BACKGROUND_TASK: User has LLM token ({user.llm_provider}), using AI-enhanced analyzer")
                print(f"BACKGROUND_TASK: User has LLM token ({user.llm_provider}), using AI-enhanced analyzer")
                # Set user context for AI analysis
                from ...services.ai_burnout_analyzer import set_user_context
                set_user_context(user)
            else:
                logger.info(f"BACKGROUND_TASK: User has no LLM token, using standard analyzer")
                print(f"BACKGROUND_TASK: User has no LLM token, using standard analyzer")
        else:
            logger.info(f"BACKGROUND_TASK: AI not enabled or no user_id, using standard analyzer")
            print(f"BACKGROUND_TASK: AI not enabled or no user_id, using standard analyzer")
        
        logger.info(f"BACKGROUND_TASK: Final analyzer decision - use_ai_analyzer: {use_ai_analyzer}")
        print(f"BACKGROUND_TASK: Final analyzer decision - use_ai_analyzer: {use_ai_analyzer}")
        
        # Check if we should use the new UnifiedBurnoutAnalyzer (feature flag)
        use_unified_analyzer = os.getenv('USE_UNIFIED_ANALYZER', 'false').lower() == 'true'
        logger.info(f"BACKGROUND_TASK: Feature flag - USE_UNIFIED_ANALYZER: {use_unified_analyzer}")
        print(f"BACKGROUND_TASK: Feature flag - USE_UNIFIED_ANALYZER: {use_unified_analyzer}")
        
        if use_unified_analyzer:
            # NEW UNIFIED ANALYZER PATH (TESTING)
            logger.info(f"BACKGROUND_TASK: 🔬 TESTING MODE - Using UnifiedBurnoutAnalyzer")
            print(f"BACKGROUND_TASK: 🔬 TESTING MODE - Using UnifiedBurnoutAnalyzer")
            
            # Set user context for AI analysis if needed
            if use_ai_analyzer:
                from ...services.ai_burnout_analyzer import set_user_context
                set_user_context(user)
                logger.info(f"BACKGROUND_TASK: 🔬 Set user context for AI analysis (LLM provider: {user.llm_provider if user.llm_token else 'none'})")
            
            analyzer_service = UnifiedBurnoutAnalyzer(
                api_token=api_token,
                platform=platform,
                enable_ai=use_ai_analyzer,
                github_token=github_token if include_github else None,
                slack_token=slack_token if include_slack else None
            )
            logger.info(f"BACKGROUND_TASK: 🔬 UnifiedBurnoutAnalyzer initialized - Features: AI={use_ai_analyzer}, GitHub={include_github}, Slack={include_slack}")
        else:
            # EXISTING ANALYZER SELECTION LOGIC (PRODUCTION)
            logger.info(f"BACKGROUND_TASK: 🏭 PRODUCTION MODE - Using legacy analyzers")
            print(f"BACKGROUND_TASK: 🏭 PRODUCTION MODE - Using legacy analyzers")
        
            # Platform-agnostic analyzer selection based on AI enablement and GitHub/Slack requirements
            needs_github_slack = include_github or include_slack
            logger.info(f"BACKGROUND_TASK: GitHub/Slack requirements - needs_github_slack: {needs_github_slack} (include_github: {include_github}, include_slack: {include_slack})")
            print(f"BACKGROUND_TASK: GitHub/Slack requirements - needs_github_slack: {needs_github_slack} (include_github: {include_github}, include_slack: {include_slack})")
            
            if use_ai_analyzer:
                analyzer_service = BurnoutAnalyzerService(api_token, platform=platform)
                logger.info(f"BACKGROUND_TASK: Using BurnoutAnalyzerService (AI-enhanced) for {platform}")
                print(f"BACKGROUND_TASK: Using BurnoutAnalyzerService (AI-enhanced) for {platform}")
            elif needs_github_slack:
                # Use full analyzer for GitHub/Slack even without AI
                analyzer_service = BurnoutAnalyzerService(api_token, platform=platform)
                logger.info(f"BACKGROUND_TASK: Using BurnoutAnalyzerService (GitHub/Slack support) for {platform}")
                print(f"BACKGROUND_TASK: Using BurnoutAnalyzerService (GitHub/Slack support) for {platform}")
            else:
                # Use platform-specific basic analyzers when neither AI nor GitHub/Slack is needed
                if platform == "pagerduty":
                    analyzer_service = PagerDutyBurnoutAnalyzerService(api_token)
                    logger.info(f"BACKGROUND_TASK: Using PagerDutyBurnoutAnalyzerService (basic)")
                    print(f"BACKGROUND_TASK: Using PagerDutyBurnoutAnalyzerService (basic)")
                else:  # Default to Rootly for backward compatibility
                    from ...core.simple_burnout_analyzer import SimpleBurnoutAnalyzer
                    analyzer_service = SimpleBurnoutAnalyzer(api_token)
                    logger.info(f"BACKGROUND_TASK: Using SimpleBurnoutAnalyzer (basic)")
                    print(f"BACKGROUND_TASK: Using SimpleBurnoutAnalyzer (basic)")
        
        # Run the analysis with timeout (15 minutes max)
        logger.info(f"BACKGROUND_TASK: Starting burnout analysis with 15-minute timeout for analysis {analysis_id}")
        try:
            # Ensure analyzer_service is properly initialized
            if not analyzer_service:
                raise Exception("Analyzer service is None - initialization failed")
            
            # Log analyzer type for debugging
            logger.info(f"BACKGROUND_TASK: Using analyzer type: {type(analyzer_service).__name__}")
            
            # Call analyzer with appropriate API based on type
            if use_unified_analyzer:
                # UnifiedBurnoutAnalyzer has simpler API (tokens passed in constructor)
                logger.info(f"BACKGROUND_TASK: 🔬 Calling UnifiedBurnoutAnalyzer.analyze_burnout()")
                results = await asyncio.wait_for(
                    analyzer_service.analyze_burnout(
                        time_range_days=time_range,
                        include_weekends=include_weekends,
                        user_id=user_id,
                        analysis_id=analysis_id
                    ),
                    timeout=900.0  # 15 minutes
                )
            else:
                # Legacy analyzers have complex API (tokens passed as parameters)
                logger.info(f"BACKGROUND_TASK: 🏭 Calling {type(analyzer_service).__name__}.analyze_burnout()")
                results = await asyncio.wait_for(
                    analyzer_service.analyze_burnout(
                        time_range_days=time_range,
                        include_weekends=include_weekends,
                        include_github=include_github,
                        include_slack=include_slack,
                        github_token=github_token,
                        slack_token=slack_token
                    ),
                    timeout=900.0  # 15 minutes
                )
            
            # Validate results
            if not results:
                logger.warning(f"BACKGROUND_TASK: Analysis {analysis_id} returned empty results")
                results = {"error": "Analysis completed but returned empty results"}
            
            logger.info(f"BACKGROUND_TASK: Analysis {analysis_id} completed successfully with {len(str(results))} characters of results")
            
            # A/B Testing: Log comparative metrics for monitoring
            try:
                analyzer_type = "unified" if use_unified_analyzer else "legacy"
                daily_trends_count = len(results.get("daily_trends", [])) if results else 0
                team_members_count = len(results.get("team_analysis", {}).get("members", [])) if results else 0
                ai_enhanced = results.get("ai_enhanced", False) if results else False
                
                logger.info(f"🔬 A/B_TESTING_METRICS: analysis_id={analysis_id}, analyzer_type={analyzer_type}, "
                           f"daily_trends_count={daily_trends_count}, team_members_count={team_members_count}, "
                           f"ai_enhanced={ai_enhanced}, platform={platform}, "
                           f"features=AI:{use_ai_analyzer},GitHub:{include_github},Slack:{include_slack}")
                
                # Log specific result structure for comparison
                if results:
                    result_keys = list(results.keys())
                    logger.info(f"🔬 A/B_TESTING_STRUCTURE: analysis_id={analysis_id}, analyzer_type={analyzer_type}, "
                               f"result_keys={result_keys}")
                    
            except Exception as monitoring_error:
                logger.warning(f"A/B testing monitoring failed: {monitoring_error}")
            
            # Update analysis with results
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "completed"
                analysis.results = results
                analysis.completed_at = datetime.now()
                db.commit()
                logger.info(f"BACKGROUND_TASK: Successfully saved results for analysis {analysis_id}")
            else:
                logger.error(f"BACKGROUND_TASK: Analysis {analysis_id} not found when trying to save results")
                
        except asyncio.TimeoutError:
            # Handle timeout
            logger.error(f"BACKGROUND_TASK: Analysis {analysis_id} timed out after 15 minutes")
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = "Analysis timed out after 15 minutes"
                analysis.completed_at = datetime.now()
                db.commit()
                logger.info(f"BACKGROUND_TASK: Updated analysis {analysis_id} status to failed due to timeout")
                
        except Exception as analysis_error:
            # Handle analysis-specific errors
            logger.error(f"BACKGROUND_TASK: Analysis {analysis_id} failed: {analysis_error}")
            
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                # Check if this is a permission error - if so, fail immediately
                error_message = str(analysis_error)
                if "Cannot access incidents endpoint" in error_message or "incidents:read" in error_message:
                    logger.error(f"BACKGROUND_TASK: Permission error detected for analysis {analysis_id}, failing immediately")
                    analysis.status = "failed"
                    analysis.error_message = error_message
                    analysis.completed_at = datetime.now()
                    db.commit()
                    return
                
                # For other errors, try to collect raw data even if analysis failed
                try:
                    logger.info(f"BACKGROUND_TASK: Attempting to save raw data for failed analysis {analysis_id}")
                    raw_data = None
                    
                    # Access the appropriate client based on platform with comprehensive error handling
                    try:
                        # Check if analyzer_service exists and is not None
                        if analyzer_service is None:
                            logger.warning(f"BACKGROUND_TASK: analyzer_service is None for analysis {analysis_id}")
                        elif hasattr(analyzer_service, 'client'):
                            client = getattr(analyzer_service, 'client', None)
                            if client is not None:
                                try:
                                    logger.info(f"BACKGROUND_TASK: Attempting raw data collection with client type: {type(client).__name__}")
                                    raw_data = await client.collect_analysis_data(days_back=time_range)
                                    logger.info(f"BACKGROUND_TASK: Successfully collected raw data for analysis {analysis_id}")
                                except Exception as client_error:
                                    logger.warning(f"BACKGROUND_TASK: Failed to collect raw data for analysis {analysis_id}: {client_error}")
                            else:
                                logger.warning(f"BACKGROUND_TASK: analyzer_service.client is None for analysis {analysis_id}")
                        else:
                            logger.warning(f"BACKGROUND_TASK: analyzer_service has no 'client' attribute for analysis {analysis_id} (type: {type(analyzer_service).__name__})")
                            
                            # Try alternative approaches for different analyzer types
                            if hasattr(analyzer_service, 'api_token'):
                                try:
                                    # For SimpleBurnoutAnalyzer or similar, try to create a client
                                    from ...core.rootly_client import RootlyAPIClient
                                    temp_client = RootlyAPIClient(analyzer_service.api_token)
                                    raw_data = await temp_client.collect_analysis_data(days_back=time_range)
                                    logger.info(f"BACKGROUND_TASK: Successfully collected raw data using temporary client for analysis {analysis_id}")
                                except Exception as temp_client_error:
                                    logger.warning(f"BACKGROUND_TASK: Failed to collect raw data using temporary client for analysis {analysis_id}: {temp_client_error}")
                    except Exception as client_access_error:
                        logger.error(f"BACKGROUND_TASK: Error accessing client for raw data collection in analysis {analysis_id}: {client_access_error}")
                    
                    # Save partial results with raw data (safely handle None raw_data)
                    try:
                        partial_results = {
                            "error": f"Analysis failed: {str(analysis_error)}",
                            "partial_data": {
                                "users": [],
                                "incidents": [],
                                "metadata": {}
                            },
                            "data_collection_successful": False,
                            "failure_stage": "analysis_processing"
                        }
                        
                        # Safely extract data if raw_data exists
                        if raw_data and isinstance(raw_data, dict):
                            try:
                                users_data = raw_data.get("users")
                                if users_data and isinstance(users_data, list):
                                    partial_results["partial_data"]["users"] = users_data
                                    
                                incidents_data = raw_data.get("incidents")
                                if incidents_data and isinstance(incidents_data, list):
                                    partial_results["partial_data"]["incidents"] = incidents_data
                                    
                                metadata_data = raw_data.get("collection_metadata")
                                if metadata_data and isinstance(metadata_data, dict):
                                    partial_results["partial_data"]["metadata"] = metadata_data
                                    
                                partial_results["data_collection_successful"] = True
                            except Exception as extract_error:
                                logger.warning(f"BACKGROUND_TASK: Error extracting partial data for analysis {analysis_id}: {extract_error}")
                    except Exception as partial_error:
                        logger.error(f"BACKGROUND_TASK: Error creating partial results for analysis {analysis_id}: {partial_error}")
                        partial_results = {
                            "error": f"Analysis failed: {str(analysis_error)}",
                            "partial_data": {"users": [], "incidents": [], "metadata": {}},
                            "data_collection_successful": False,
                            "failure_stage": "analysis_processing"
                        }
                    
                    analysis.status = "failed"
                    analysis.error_message = f"Analysis failed: {str(analysis_error)}"
                    analysis.results = partial_results
                    analysis.completed_at = datetime.now()
                    db.commit()
                    logger.info(f"BACKGROUND_TASK: Saved partial data for failed analysis {analysis_id}")
                    
                except Exception as data_error:
                    logger.error(f"BACKGROUND_TASK: Could not save partial data for analysis {analysis_id}: {data_error}")
                    analysis.status = "failed"
                    analysis.error_message = f"Analysis failed: {str(analysis_error)}"
                    analysis.completed_at = datetime.now()
                    db.commit()
        
    except Exception as e:
        # Handle any other errors (DB, etc.)
        logger.error(f"BACKGROUND_TASK: Critical error in analysis {analysis_id}: {str(e)}", exc_info=True)
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = f"Task failed: {str(e)}"
                analysis.completed_at = datetime.now()
                db.commit()
                logger.info(f"BACKGROUND_TASK: Updated analysis {analysis_id} status to failed due to critical error")
            else:
                logger.error(f"BACKGROUND_TASK: Could not find analysis {analysis_id} to update error status")
        except Exception as db_error:
            logger.error(f"BACKGROUND_TASK: Failed to update database for analysis {analysis_id}: {str(db_error)}", exc_info=True)
    
    finally:
        try:
            db.close()
        except:
            pass