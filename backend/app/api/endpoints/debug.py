from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import logging
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

from ...models import get_db, User, RootlyIntegration, Analysis, SlackIntegration, GitHubIntegration

router = APIRouter()

@router.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables"""
    return {
        "GOOGLE_REDIRECT_URI": os.getenv("GOOGLE_REDIRECT_URI", "NOT SET"),
        "GITHUB_REDIRECT_URI": os.getenv("GITHUB_REDIRECT_URI", "NOT SET"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL", "NOT SET"),
        "env_keys": list(os.environ.keys())
    }

@router.get("/debug/database")
async def debug_database(db: Session = Depends(get_db)):
    """Debug endpoint to check database connectivity and data"""
    try:
        # Test basic connectivity
        db.execute(text("SELECT 1"))
        
        # Count records in each table
        user_count = db.query(User).count()
        integration_count = db.query(RootlyIntegration).count()
        analysis_count = db.query(Analysis).count()
        
        # Get recent records
        recent_users = db.query(User).limit(3).all()
        recent_integrations = db.query(RootlyIntegration).limit(3).all()
        recent_analyses = db.query(Analysis).order_by(Analysis.id.desc()).limit(3).all()
        
        return {
            "database_connected": True,
            "counts": {
                "users": user_count,
                "integrations": integration_count,
                "analyses": analysis_count
            },
            "recent_users": [{"id": u.id, "email": u.email, "name": u.name} for u in recent_users],
            "recent_integrations": [{"id": i.id, "name": i.name, "created_at": str(i.created_at)} for i in recent_integrations],
            "recent_analyses": [{"id": a.id, "status": a.status, "created_at": str(a.created_at)} for a in recent_analyses]
        }
    except Exception as e:
        return {
            "database_connected": False,
            "error": str(e)
        }


@router.get("/debug/analysis/{analysis_id}")
async def debug_analysis(analysis_id: int, db: Session = Depends(get_db)):
    """Debug endpoint to diagnose failed analysis and background task issues"""
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Get the analysis record from the database
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Analysis {analysis_id} not found")
        
        analysis_info = {
            "id": analysis.id,
            "user_id": analysis.user_id,
            "integration_id": analysis.rootly_integration_id,
            "status": analysis.status,
            "error_message": analysis.error_message,
            "time_range": analysis.time_range,
            "config": analysis.config,
            "created_at": str(analysis.created_at),
            "completed_at": str(analysis.completed_at) if analysis.completed_at else None,
            "has_results": analysis.results is not None,
            "results_type": type(analysis.results).__name__ if analysis.results else None,
            "results_size": len(str(analysis.results)) if analysis.results else 0
        }
        
        # 2. Get integration information
        integration_info = {}
        if analysis.rootly_integration_id:
            integration = db.query(RootlyIntegration).filter(
                RootlyIntegration.id == analysis.rootly_integration_id
            ).first()
            
            if integration:
                integration_info = {
                    "id": integration.id,
                    "name": integration.name,
                    "organization_name": integration.organization_name,
                    "platform": integration.platform,
                    "is_active": integration.is_active,
                    "created_at": str(integration.created_at),
                    "last_used_at": str(integration.last_used_at) if integration.last_used_at else None,
                    "total_users": integration.total_users,
                    "has_api_token": bool(integration.api_token)
                }
                
                # 3. Test the integration's API connection
                api_test_result = await test_integration_connection(integration, logger)
                integration_info["api_test"] = api_test_result
            else:
                integration_info = {"error": f"Integration {analysis.rootly_integration_id} not found"}
        else:
            integration_info = {"error": "No integration ID in analysis record"}
        
        # 4. Get user information and check for additional integrations
        user_info = {}
        additional_integrations = {}
        if analysis.user_id:
            user = db.query(User).filter(User.id == analysis.user_id).first()
            if user:
                user_info = {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "has_llm_token": user.llm_token is not None,
                    "llm_provider": user.llm_provider,
                    "created_at": str(user.created_at) if hasattr(user, 'created_at') else None
                }
                
                # Check for Slack and GitHub integrations
                slack_integration = db.query(SlackIntegration).filter(
                    SlackIntegration.user_id == analysis.user_id
                ).first()
                
                github_integration = db.query(GitHubIntegration).filter(
                    GitHubIntegration.user_id == analysis.user_id
                ).first()
                
                additional_integrations = {
                    "slack": {
                        "exists": slack_integration is not None,
                        "has_token": slack_integration.slack_token is not None if slack_integration else False,
                        "workspace_id": slack_integration.workspace_id if slack_integration else None,
                        "slack_user_id": slack_integration.slack_user_id if slack_integration else None
                    } if slack_integration else {"exists": False},
                    "github": {
                        "exists": github_integration is not None,
                        "has_token": github_integration.github_token is not None if github_integration else False,
                        "username": github_integration.github_username if github_integration else None,
                        "organizations": github_integration.organizations if github_integration else []
                    } if github_integration else {"exists": False}
                }
            else:
                user_info = {"error": f"User {analysis.user_id} not found"}
        
        # 5. Check for recent log entries (simulate - in a real scenario, you'd query a logging system)
        log_analysis = await analyze_background_task_logs(analysis_id, logger)
        
        # 6. Background task execution analysis
        background_task_info = {
            "task_likely_started": analysis.status in ["running", "completed", "failed"],
            "task_completed": analysis.status in ["completed", "failed"],
            "task_timeout_likely": (
                analysis.error_message and "timed out" in analysis.error_message.lower()
            ) if analysis.error_message else False,
            "permission_error_likely": (
                analysis.error_message and 
                ("cannot access" in analysis.error_message.lower() or 
                 "incidents:read" in analysis.error_message.lower())
            ) if analysis.error_message else False,
            "null_results_reason": determine_null_results_reason(analysis)
        }
        
        # 7. Diagnosis and recommendations
        diagnosis = generate_diagnosis(analysis, integration_info, background_task_info)
        
        return {
            "analysis": analysis_info,
            "integration": integration_info,
            "user": user_info,
            "additional_integrations": additional_integrations,
            "background_task": background_task_info,
            "log_analysis": log_analysis,
            "diagnosis": diagnosis,
            "debug_timestamp": str(datetime.now())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Debug analysis failed for ID {analysis_id}: {str(e)}", exc_info=True)
        return {
            "error": f"Debug analysis failed: {str(e)}",
            "traceback": traceback.format_exc(),
            "debug_timestamp": str(datetime.now())
        }


async def test_integration_connection(integration: RootlyIntegration, logger) -> Dict[str, Any]:
    """Test the integration's API connection"""
    try:
        if integration.platform == "pagerduty":
            # Test PagerDuty API connection
            from ...core.pagerduty_client import PagerDutyAPIClient
            client = PagerDutyAPIClient(integration.api_token)
            
            try:
                # Test basic API access with a simple call
                result = await client.test_connection()
                return {
                    "success": True,
                    "platform": "pagerduty",
                    "message": "API connection successful",
                    "details": result
                }
            except Exception as api_error:
                return {
                    "success": False,
                    "platform": "pagerduty",
                    "error": str(api_error),
                    "error_type": type(api_error).__name__
                }
                
        elif integration.platform == "rootly":
            # Test Rootly API connection
            from ...core.rootly_client import RootlyAPIClient
            client = RootlyAPIClient(integration.api_token)
            
            try:
                # Test basic API access
                result = await client.test_connection()
                return {
                    "success": True,
                    "platform": "rootly",
                    "message": "API connection successful",
                    "details": result
                }
            except Exception as api_error:
                return {
                    "success": False,
                    "platform": "rootly",
                    "error": str(api_error),
                    "error_type": type(api_error).__name__
                }
        else:
            return {
                "success": False,
                "error": f"Unknown platform: {integration.platform}"
            }
            
    except Exception as e:
        logger.error(f"Error testing integration connection: {str(e)}")
        return {
            "success": False,
            "error": f"Connection test failed: {str(e)}",
            "error_type": type(e).__name__
        }


async def analyze_background_task_logs(analysis_id: int, logger) -> Dict[str, Any]:
    """Analyze logs for background task execution"""
    try:
        # Try to read recent log entries from the log file
        log_file_path = "/Users/spencercheng/Workspace/Rootly/rootly-burnout-detector-web/backend/backend.log"
        
        analysis_logs = []
        search_patterns = [
            f"analysis {analysis_id}",
            f"analysis_id={analysis_id}",
            f"BACKGROUND_TASK.*{analysis_id}",
            f"ENDPOINT.*{analysis_id}"
        ]
        
        try:
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                
            # Look for relevant log entries
            for line in lines[-1000:]:  # Check last 1000 lines
                for pattern in search_patterns:
                    if pattern.lower() in line.lower():
                        analysis_logs.append(line.strip())
                        break
                        
            return {
                "log_entries_found": len(analysis_logs),
                "recent_logs": analysis_logs[-20:] if analysis_logs else [],  # Last 20 relevant entries
                "log_file_accessible": True
            }
            
        except FileNotFoundError:
            return {
                "log_entries_found": 0,
                "recent_logs": [],
                "log_file_accessible": False,
                "error": f"Log file not found: {log_file_path}"
            }
            
    except Exception as e:
        logger.error(f"Error analyzing logs: {str(e)}")
        return {
            "log_entries_found": 0,
            "recent_logs": [],
            "log_file_accessible": False,
            "error": f"Log analysis failed: {str(e)}"
        }


def determine_null_results_reason(analysis: Analysis) -> str:
    """Determine why analysis.results is null"""
    if analysis.results is not None:
        return "Results are not null"
    
    if analysis.status == "pending":
        return "Analysis never started - background task may not have been queued"
    elif analysis.status == "running":
        return "Analysis is still running - results not yet available"
    elif analysis.status == "failed":
        if analysis.error_message:
            if "timed out" in analysis.error_message.lower():
                return "Analysis timed out - no results saved due to timeout"
            elif "cannot access" in analysis.error_message.lower():
                return "Permission error - API access denied, no results generated"
            else:
                return f"Analysis failed with error: {analysis.error_message}"
        else:
            return "Analysis marked as failed but no error message recorded"
    elif analysis.status == "completed":
        return "Analysis marked as completed but results are null - this indicates a bug in the background task"
    else:
        return f"Unknown status '{analysis.status}' with null results"


def generate_diagnosis(analysis: Analysis, integration_info: Dict, background_task_info: Dict) -> Dict[str, Any]:
    """Generate diagnosis and recommendations based on analysis data"""
    issues = []
    recommendations = []
    severity = "info"
    
    # Check for null results
    if analysis.results is None:
        issues.append("Analysis results are null")
        severity = "critical"
        
        if analysis.status == "pending":
            issues.append("Background task never started")
            recommendations.extend([
                "Check if FastAPI background tasks are working properly",
                "Verify database connections in background task context",
                "Check for exceptions during task queuing"
            ])
            
        elif analysis.status == "failed":
            if analysis.error_message:
                if "timed out" in analysis.error_message.lower():
                    issues.append("Analysis timed out after 15 minutes")
                    recommendations.extend([
                        "Check if the API is responding slowly",
                        "Verify network connectivity to the API",
                        "Consider increasing timeout duration",
                        "Check for large datasets that might cause delays"
                    ])
                elif "cannot access" in analysis.error_message.lower():
                    issues.append("API permission denied")
                    recommendations.extend([
                        "Verify API token has correct permissions",
                        "Check if token has 'incidents:read' scope",
                        "Test API token manually",
                        "Regenerate API token if necessary"
                    ])
                else:
                    issues.append(f"Background task failed: {analysis.error_message}")
            else:
                issues.append("Background task failed without error message")
                recommendations.append("Check application logs for unhandled exceptions")
                
        elif analysis.status == "completed":
            issues.append("Analysis marked completed but has null results - critical bug")
            recommendations.extend([
                "This indicates a bug in the result saving logic",
                "Check background task implementation for result handling",
                "Verify database commit operations"
            ])
    
    # Check integration issues
    if "error" in integration_info:
        issues.append(f"Integration issue: {integration_info['error']}")
        severity = "critical"
        recommendations.append("Fix integration configuration")
    
    elif "api_test" in integration_info and not integration_info["api_test"].get("success", False):
        issues.append("API connection test failed")
        severity = "high"
        recommendations.extend([
            "Verify API token is valid and not expired",
            "Check network connectivity",
            "Verify API endpoint URLs are correct"
        ])
    
    # Background task analysis
    if not background_task_info["task_likely_started"]:
        issues.append("Background task appears to have never started")
        recommendations.extend([
            "Check FastAPI background task queue",
            "Verify task function exists and is importable",
            "Check for exceptions during task creation"
        ])
    
    return {
        "severity": severity,
        "issues": issues,
        "recommendations": recommendations,
        "summary": f"Found {len(issues)} issues with analysis {analysis.id}"
    }