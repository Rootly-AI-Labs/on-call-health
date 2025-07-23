from fastapi import APIRouter
import os

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