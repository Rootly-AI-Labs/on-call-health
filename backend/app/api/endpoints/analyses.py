"""
Burnout analysis API endpoints.
"""
import logging
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
    """Calculate daily health trends from historical analyses."""
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    # Build query for completed analyses within date range
    query = db.query(Analysis).filter(
        Analysis.user_id == current_user.id,
        Analysis.status == "completed",
        Analysis.created_at >= start_date,
        Analysis.created_at <= end_date,
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
    
    # Get all analyses and order by date
    analyses = query.order_by(Analysis.created_at.asc()).all()
    
    if not analyses:
        # Return empty trends if no historical data
        return HistoricalTrendsResponse(
            daily_trends=[],
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
    
    # Group analyses by date and calculate daily averages
    daily_data = defaultdict(list)
    
    for analysis in analyses:
        analysis_date = analysis.created_at.strftime("%Y-%m-%d")
        
        # Extract health metrics from results
        results = analysis.results
        if not results or not isinstance(results, dict):
            continue
        
        team_health = results.get("team_health", {})
        if not team_health:
            continue
        
        # Calculate metrics for this analysis
        overall_score = team_health.get("overall_score", 0.0)
        average_burnout_score = team_health.get("average_burnout_score", 0.0) 
        members_at_risk = team_health.get("members_at_risk", 0)
        health_status = team_health.get("health_status", "unknown")
        
        # Count total members from team_analysis
        team_analysis = results.get("team_analysis", [])
        total_members = len(team_analysis) if isinstance(team_analysis, list) else 0
        
        daily_data[analysis_date].append({
            "overall_score": float(overall_score),
            "average_burnout_score": float(average_burnout_score),
            "members_at_risk": int(members_at_risk),
            "total_members": int(total_members),
            "health_status": str(health_status)
        })
    
    # Calculate daily averages and create trend points
    daily_trends = []
    all_scores = []
    
    for date in sorted(daily_data.keys()):
        day_analyses = daily_data[date]
        
        # Calculate averages for the day
        avg_overall = sum(a["overall_score"] for a in day_analyses) / len(day_analyses)
        avg_burnout = sum(a["average_burnout_score"] for a in day_analyses) / len(day_analyses)
        avg_at_risk = sum(a["members_at_risk"] for a in day_analyses) / len(day_analyses)
        avg_total = sum(a["total_members"] for a in day_analyses) / len(day_analyses)
        
        # Use most common health status for the day
        status_counts = defaultdict(int)
        for a in day_analyses:
            status_counts[a["health_status"]] += 1
        most_common_status = max(status_counts.items(), key=lambda x: x[1])[0]
        
        daily_trends.append(DailyTrendPoint(
            date=date,
            overall_score=round(avg_overall, 2),
            average_burnout_score=round(avg_burnout, 2),
            members_at_risk=round(avg_at_risk),
            total_members=round(avg_total),
            health_status=most_common_status,
            analysis_count=len(day_analyses)
        ))
        
        all_scores.append(avg_overall)
    
    # Calculate trend summary
    trend_direction = "stable"
    if len(all_scores) >= 2:
        score_change = all_scores[-1] - all_scores[0]
        if score_change > 0.5:
            trend_direction = "improving"
        elif score_change < -0.5:
            trend_direction = "declining"
    
    summary = {
        "total_analyses": len(analyses),
        "days_with_data": len(daily_trends),
        "trend_direction": trend_direction,
        "average_score": round(sum(all_scores) / len(all_scores) if all_scores else 0.0, 2),
        "score_change": round(all_scores[-1] - all_scores[0] if len(all_scores) >= 2 else 0.0, 2),
        "best_day": max(daily_trends, key=lambda x: x.overall_score).date if daily_trends else None,
        "worst_day": min(daily_trends, key=lambda x: x.overall_score).date if daily_trends else None
    }
    
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
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
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
        
        # Platform-agnostic analyzer selection based on AI enablement
        if use_ai_analyzer:
            analyzer_service = BurnoutAnalyzerService(api_token, platform=platform)
            logger.info(f"BACKGROUND_TASK: Using BurnoutAnalyzerService (AI-enhanced) for {platform}")
            print(f"BACKGROUND_TASK: Using BurnoutAnalyzerService (AI-enhanced) for {platform}")
        else:
            # Use platform-specific basic analyzers when AI is not enabled
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
            logger.info(f"BACKGROUND_TASK: Analysis {analysis_id} completed successfully")
            
            # Update analysis with results
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "completed"
                analysis.results = results
                analysis.completed_at = datetime.now()
                db.commit()
                
        except asyncio.TimeoutError:
            # Handle timeout
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = "Analysis timed out after 15 minutes"
                analysis.completed_at = datetime.now()
                db.commit()
                
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
                    # Access the appropriate client based on platform
                    if platform == "pagerduty":
                        raw_data = await analyzer_service.client.collect_analysis_data(days_back=time_range)
                    else:
                        raw_data = await analyzer_service.client.collect_analysis_data(days_back=time_range)
                    
                    # Save partial results with raw data
                    partial_results = {
                        "error": f"Analysis failed: {str(analysis_error)}",
                        "partial_data": {
                            "users": raw_data.get("users", []) if raw_data else [],
                            "incidents": raw_data.get("incidents", []) if raw_data else [],
                            "metadata": raw_data.get("collection_metadata", {}) if raw_data else {}
                        },
                        "data_collection_successful": bool(raw_data),
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
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = f"Task failed: {str(e)}"
                analysis.completed_at = datetime.now()
                db.commit()
        except:
            pass  # If we can't even update the DB, just let it fail
    
    finally:
        try:
            db.close()
        except:
            pass