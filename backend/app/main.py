"""
FastAPI main application for On-call Burnout Detector.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.errors import RateLimitExceeded
from .models import create_tables
from .core.config import settings
from .core.rate_limiting import limiter, custom_rate_limit_exceeded_handler
from .middleware.security import security_middleware
from .middleware.user_logging import user_logging_middleware
from .middleware.logging_context import UserContextFilter
from .api.endpoints import auth, rootly, analysis, analyses, pagerduty, github, slack, jira, linear, llm, mappings, manual_mappings, debug_mappings, migrate, admin, notifications, invitations, surveys

# Configure logging based on environment variable
LOG_LEVEL = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

# Create and configure the UserContextFilter to add user identity to all log records
user_context_filter = UserContextFilter()

# Configure logging with user identifier (email preferred) in the format
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - [user_id=%(user_id)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Add user context filter to root logger and all handlers
# This ensures user_id is set before formatting for %(user_id)s to work
root_logger = logging.getLogger()
root_logger.addFilter(user_context_filter)
for handler in root_logger.handlers:
    handler.addFilter(user_context_filter)

# Store reference for handlers added later (e.g., by uvicorn)
logging.user_context_filter = user_context_filter

# Set specific loggers to WARNING in production to reduce noise
if settings.ENVIRONMENT == "production" or LOG_LEVEL >= logging.WARNING:
    # Reduce verbosity for noisy modules
    logging.getLogger("app.api.endpoints.slack").setLevel(logging.WARNING)
    logging.getLogger("app.services.survey_scheduler").setLevel(logging.WARNING)
    logging.getLogger("app.middleware.security").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(f"Starting application with log level: {settings.LOG_LEVEL}")

# Create FastAPI application
app = FastAPI(
    title="On-Call Health API",
    description="API for monitoring team wellbeing and detecting burnout risk in engineering teams",
    version="1.0.0",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 1,  # Don't expand schemas deeply
        "syntaxHighlight.theme": "monokai",
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Mount static files for favicon
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Add rate limiting to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# Add GZip compression middleware (must be added before other middleware)
# Compresses responses > 1KB with gzip, typically achieves 70-90% compression for JSON
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add security middleware
app.middleware("http")(security_middleware)

# Add user logging middleware (sets user context for all logs)
app.middleware("http")(user_logging_middleware)

# Configure CORS - Secure configuration
def get_cors_origins() -> list[str]:
    """Get allowed CORS origins based on environment."""
    # Start with configured frontend URL
    origins = [settings.FRONTEND_URL]

    # Development origins - localhost and 127.0.0.1 on common Next.js ports
    dev_ports = ["3000", "3001", "3002"]
    origins.extend(f"http://{host}:{port}" for host in ["localhost", "127.0.0.1"] for port in dev_ports)

    # Production domains
    origins.extend(["https://www.oncallburnout.com", "https://oncallburnout.com"])

    # Optional environment-based origins
    production_frontend = os.getenv("PRODUCTION_FRONTEND_URL")
    if production_frontend:
        origins.append(production_frontend)

    vercel_url = os.getenv("VERCEL_URL")
    if vercel_url:
        origins.append(f"https://{vercel_url}")

    # Remove duplicates while preserving order
    unique_origins = list(dict.fromkeys(origins))
    logger.info(f"CORS allowed origins: {unique_origins}")

    return unique_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),  # Specific allowed origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Cache-Control",
        "Pragma"
    ],  # Specific headers only
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "On-Call Health API", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "on-call-health"}

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    """Serve favicon for the API documentation."""
    return FileResponse("app/static/favicon.svg", media_type="image/svg+xml")

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    # Add user context filter to any handlers added by uvicorn after initial setup
    for handler in logging.getLogger().handlers:
        if user_context_filter not in handler.filters:
            handler.addFilter(user_context_filter)

    create_tables()

    # Run database migrations
    try:
        from migrations.migration_runner import run_migrations
        print("🔧 Running database migrations...")
        success = run_migrations()
        if success:
            print("✅ All migrations applied successfully")
        else:
            print("⚠️  Some migrations failed - check logs")
    except Exception as e:
        print(f"⚠️  Migration runner failed: {e}")

    # Start survey scheduler
    from app.services.survey_scheduler import survey_scheduler
    from app.models import SessionLocal

    survey_scheduler.start()
    print("✅ Survey scheduler started")

    # Load existing schedules from database
    db = SessionLocal()
    try:
        survey_scheduler.schedule_organization_surveys(db)
        print("✅ Loaded survey schedules from database")
    except Exception as e:
        print(f"⚠️ Error loading survey schedules: {str(e)}")
    finally:
        db.close()

    # Clean up stuck analyses (analyses that have been "running" for too long)
    await cleanup_stuck_analyses()


async def cleanup_stuck_analyses():
    """
    Mark analyses that have been stuck in 'running' status for too long as failed.
    This handles cases where the server crashed/restarted while an analysis was running.
    """
    from app.models import SessionLocal, Analysis

    # Analyses running for more than 30 minutes are considered stuck
    stuck_threshold = timedelta(minutes=30)
    cutoff_time = datetime.now(timezone.utc) - stuck_threshold

    db = SessionLocal()
    try:
        # Find all analyses that have been running for too long
        stuck_analyses = db.query(Analysis).filter(
            Analysis.status == "running",
            Analysis.created_at < cutoff_time
        ).all()

        if stuck_analyses:
            print(f"🔧 Found {len(stuck_analyses)} stuck analyses to clean up")
            cleaned_count = 0
            for analysis in stuck_analyses:
                try:
                    # Re-check status to avoid race conditions
                    db.refresh(analysis)
                    if analysis.status != "running":
                        print(f"  - Skipping analysis {analysis.id} (status changed to {analysis.status})")
                        continue

                    analysis.status = "failed"
                    analysis.error_message = "Analysis was interrupted (server restart). Please run a new analysis."
                    analysis.completed_at = datetime.now(timezone.utc)
                    db.commit()
                    cleaned_count += 1
                    print(f"  - Marked analysis {analysis.id} as failed (was running since {analysis.created_at})")
                except Exception as e:
                    print(f"  - Failed to clean up analysis {analysis.id}: {str(e)}")
                    db.rollback()

            print(f"✅ Cleaned up {cleaned_count} stuck analyses")
        else:
            print("✅ No stuck analyses found")
    except Exception as e:
        print(f"⚠️ Error cleaning up stuck analyses: {str(e)}")
    finally:
        db.close()


# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(rootly.router, prefix="/rootly", tags=["rootly"])
app.include_router(pagerduty.router, prefix="/pagerduty", tags=["pagerduty"])
app.include_router(analyses.router, prefix="/analyses", tags=["analyses"])
app.include_router(github.router, prefix="/integrations", tags=["github-integration"])
app.include_router(slack.router, prefix="/integrations", tags=["slack-integration"])
app.include_router(jira.router, prefix="/integrations", tags=["jira-integration"])
app.include_router(linear.router, prefix="/integrations", tags=["linear-integration"])
app.include_router(llm.router, tags=["llm-tokens"])
app.include_router(mappings.router, prefix="/integrations", tags=["integration-mappings"])
app.include_router(manual_mappings.router, prefix="/integrations", tags=["manual-mappings"])
app.include_router(debug_mappings.router, prefix="/api", tags=["debug"])
app.include_router(migrate.router, prefix="/api/migrate", tags=["migration"])
app.include_router(admin.router, prefix="/api", tags=["admin"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(invitations.router, prefix="/api", tags=["invitations"])
app.include_router(surveys.router, prefix="/api/surveys", tags=["surveys"])
logger.debug("Surveys router registered successfully")
