"""
Burnout analysis API endpoints.
"""
import logging
from datetime import datetime
from typing import List, Optional
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


class AnalysisResponse(BaseModel):
    id: int
    integration_id: int
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    time_range: int
    analysis_data: Optional[dict]


class AnalysisListResponse(BaseModel):
    analyses: List[AnalysisResponse]
    total: int


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
            user_id=current_user.id
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


async def run_analysis_task(
    analysis_id: int,
    integration_id: int,
    api_token: str,
    platform: str,
    time_range: int,
    include_weekends: bool,
    include_github: bool = False,
    include_slack: bool = False,
    user_id: int = None
):
    """Background task to run the actual burnout analysis."""
    import asyncio
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"BACKGROUND_TASK: Starting analysis {analysis_id} with timeout mechanism")
    logger.info(f"BACKGROUND_TASK: GitHub/Slack params - include_github: {include_github}, include_slack: {include_slack}")
    logger.info(f"BACKGROUND_TASK: User ID received: {user_id}")
    print(f"BACKGROUND_TASK: GitHub/Slack params - include_github: {include_github}, include_slack: {include_slack}")
    print(f"BACKGROUND_TASK: User ID received: {user_id}")
    
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

        # Initialize analyzer service based on platform
        logger.info(f"BACKGROUND_TASK: Initializing {platform} analyzer service for analysis {analysis_id}")
        if platform == "pagerduty":
            analyzer_service = PagerDutyBurnoutAnalyzerService(api_token)
        else:  # Default to Rootly for backward compatibility
            analyzer_service = BurnoutAnalyzerService(api_token)
        
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