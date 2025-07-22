"""
Burnout analysis API endpoints.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...models import get_db, User, Analysis
from ...auth.dependencies import get_current_active_user
from ...core.rootly_client import RootlyAPIClient
from ...core.simple_burnout_analyzer import SimpleBurnoutAnalyzer
from ...services.burnout_analyzer import BurnoutAnalyzerService

logger = logging.getLogger(__name__)
router = APIRouter()

class AnalysisRequest(BaseModel):
    days_back: int = 30
    include_weekends: bool = True

class AnalysisResponse(BaseModel):
    analysis_id: int
    status: str
    message: str

@router.post("/start", response_model=AnalysisResponse)
async def start_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Start a new burnout analysis."""
    if not current_user.rootly_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No Rootly token configured. Please set your token first."
        )
    
    # Create analysis record
    analysis = Analysis(
        user_id=current_user.id,
        status="pending",
        config={
            "days_back": request.days_back,
            "include_weekends": request.include_weekends
        }
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    # Start analysis in background
    background_tasks.add_task(
        run_analysis_task,
        analysis.id,
        current_user.rootly_token,
        request.days_back,
        current_user.id  # Pass user ID for LLM token access
    )
    
    return AnalysisResponse(
        analysis_id=analysis.id,
        status="started",
        message=f"Analysis started. This usually takes 2-3 minutes for {request.days_back} days of data."
    )

@router.get("/{analysis_id}")
async def get_analysis_status(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get analysis status and progress."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    response = {
        "id": analysis.id,
        "status": analysis.status,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
        "config": analysis.config
    }
    
    if analysis.error_message:
        response["error"] = analysis.error_message
    
    if analysis.results:
        response["results_summary"] = {
            "total_users": len(analysis.results.get("team_analysis", [])),
            "high_risk_count": len([
                u for u in analysis.results.get("team_analysis", [])
                if u.get("risk_level") == "high"
            ]),
            "team_average_score": analysis.results.get("team_summary", {}).get("average_score")
        }
    
    return response

@router.get("/{analysis_id}/results")
async def get_analysis_results(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get complete analysis results."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found"
        )
    
    if analysis.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Analysis not completed yet. Current status: {analysis.status}"
        )
    
    return analysis.results

@router.get("/current")
async def get_current_analysis(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get the most recent analysis for the user."""
    analysis = db.query(Analysis).filter(
        Analysis.user_id == current_user.id
    ).order_by(Analysis.created_at.desc()).first()
    
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analyses found"
        )
    
    response = {
        "id": analysis.id,
        "status": analysis.status,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
        "config": analysis.config
    }
    
    if analysis.status == "completed" and analysis.results:
        response["results"] = analysis.results
    elif analysis.error_message:
        response["error"] = analysis.error_message
    
    return response

@router.get("/history")
async def get_analysis_history(
    limit: int = 10,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get user's analysis history."""
    analyses = db.query(Analysis).filter(
        Analysis.user_id == current_user.id
    ).order_by(Analysis.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": analysis.id,
            "status": analysis.status,
            "created_at": analysis.created_at,
            "completed_at": analysis.completed_at,
            "config": analysis.config,
            "has_results": bool(analysis.results)
        }
        for analysis in analyses
    ]

async def run_analysis_task(analysis_id: int, rootly_token: str, days_back: int, user_id: int):
    """Background task to run the actual analysis."""
    db = next(get_db())
    
    try:
        # Update status to running
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        analysis.status = "running"
        db.commit()
        
        # Get user for LLM token access
        user = db.query(User).filter(User.id == user_id).first()
        has_llm_token = user and user.llm_token and user.llm_provider
        
        # Initialize analyzer - use full analyzer if LLM token available, simple otherwise
        if has_llm_token:
            logger.info(f"User has LLM token ({user.llm_provider}), using full analyzer with AI enhancement")
            
            # Set user context for AI analysis
            from ...services.ai_burnout_analyzer import set_user_context
            set_user_context(user)
            
            analyzer = BurnoutAnalyzerService(rootly_token)
            
            # Run full analysis with AI enhancement
            results = await analyzer.analyze_burnout(
                time_range_days=days_back,
                include_weekends=True,
                include_github=False,  # TODO: Add GitHub integration flags
                include_slack=False    # TODO: Add Slack integration flags
            )
        else:
            logger.info("No LLM token available, using simple analyzer")
            # Initialize Rootly client
            client = RootlyAPIClient(rootly_token)
            
            # Collect data
            raw_data = await client.collect_analysis_data(days_back=days_back)
            
            # Initialize simple analyzer
            analyzer = SimpleBurnoutAnalyzer()
            
            # Run simple analysis
            results = analyzer.analyze_team_burnout(
                users=raw_data["users"],
                incidents=raw_data["incidents"],
                metadata=raw_data["collection_metadata"]
            )
        
        # Update analysis with results
        analysis.status = "completed"
        analysis.results = results
        analysis.completed_at = datetime.now()
        db.commit()
        
    except Exception as e:
        # Update analysis with error
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        analysis.status = "failed"
        analysis.error_message = str(e)
        db.commit()
    
    finally:
        db.close()