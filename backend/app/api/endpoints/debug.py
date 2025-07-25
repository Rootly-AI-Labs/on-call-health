from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

from ...models import get_db, User, RootlyIntegration, Analysis

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