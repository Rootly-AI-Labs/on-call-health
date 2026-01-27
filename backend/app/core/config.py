"""
Configuration settings for the application.
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "For local development, use PostgreSQL (e.g., postgresql://user:password@localhost/dbname)"
        )
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Frontend URL for survey links
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # OAuth - Google
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # OAuth - GitHub
    GITHUB_CLIENT_ID: Optional[str] = os.getenv("GITHUB_CLIENT_ID") 
    GITHUB_CLIENT_SECRET: Optional[str] = os.getenv("GITHUB_CLIENT_SECRET")
    GITHUB_REDIRECT_URI: str = os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/github/callback")
    
    # OAuth - Slack
    SLACK_CLIENT_ID: Optional[str] = os.getenv("SLACK_CLIENT_ID")
    SLACK_CLIENT_SECRET: Optional[str] = os.getenv("SLACK_CLIENT_SECRET")
    SLACK_SIGNING_SECRET: Optional[str] = os.getenv("SLACK_SIGNING_SECRET")
    SLACK_REDIRECT_URI: str = os.getenv("SLACK_REDIRECT_URI", "http://localhost:8000/auth/slack/callback")

    # OAuth - Jira
    JIRA_CLIENT_ID: Optional[str] = os.getenv("JIRA_CLIENT_ID")
    JIRA_CLIENT_SECRET: Optional[str] = os.getenv("JIRA_CLIENT_SECRET")

    # OAuth - Linear
    LINEAR_CLIENT_ID: Optional[str] = os.getenv("LINEAR_CLIENT_ID")
    LINEAR_CLIENT_SECRET: Optional[str] = os.getenv("LINEAR_CLIENT_SECRET")

    # Environment detection
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Rootly API
    ROOTLY_API_BASE_URL: str = os.getenv("ROOTLY_API_BASE_URL", "https://api.rootly.com")

    # Working Hours Configuration
    # These define what is considered "business hours" for burnout analysis
    # Hours are in 24-hour format (0-23) and applied in each user's local timezone
    BUSINESS_HOURS_START: int = int(os.getenv("BUSINESS_HOURS_START", "9"))   # 9 AM
    BUSINESS_HOURS_END: int = int(os.getenv("BUSINESS_HOURS_END", "17"))      # 5 PM
    LATE_NIGHT_START: int = int(os.getenv("LATE_NIGHT_START", "22"))          # 10 PM
    LATE_NIGHT_END: int = int(os.getenv("LATE_NIGHT_END", "6"))               # 6 AM

    # ARQ (Async Redis Queue) Configuration
    # Use separate Redis database for ARQ to avoid key collisions
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    # Construct ARQ Redis URL with db=1 (separate database from main app)
    _redis_base = REDIS_URL.rstrip('/').split('?')[0]  # Remove trailing slash and query params
    if '/' in _redis_base.split('://')[-1]:  # Check if db number already specified
        _redis_base = '/'.join(_redis_base.split('/')[:-1])  # Remove existing db number
    ARQ_REDIS_URL: str = os.getenv("ARQ_REDIS_URL", f"{_redis_base}/1")  # Use db=1 for ARQ
    ARQ_MAX_CONNECTIONS: int = int(os.getenv("ARQ_MAX_CONNECTIONS", "10"))
    ARQ_TIMEOUT: int = int(os.getenv("ARQ_TIMEOUT", "30"))  # seconds
    ARQ_RETRY_JOBS: bool = os.getenv("ARQ_RETRY_JOBS", "true").lower() == "true"
    ARQ_KEEP_RESULT: int = int(os.getenv("ARQ_KEEP_RESULT", "3600"))  # 1 hour in seconds

settings = Settings()