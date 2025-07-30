"""
FastAPI main application for Rootly Burnout Detector.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import create_tables
from .api.endpoints import auth, rootly, analysis, analyses, pagerduty, github, slack, llm, debug, mappings, manual_mappings, migration

# Create FastAPI application
app = FastAPI(
    title="Rootly Burnout Detector API",
    description="API for detecting burnout risk in engineering teams using Rootly incident data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Rootly Burnout Detector API", "version": "1.0.0"}

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "rootly-burnout-detector"}

# Initialize database tables
@app.on_event("startup")
async def startup_event():
    create_tables()
    
    # Auto-cleanup duplicate mappings from before Phase 1 fixes
    try:
        import sys
        from pathlib import Path
        backend_path = Path(__file__).parent.parent
        sys.path.insert(0, str(backend_path))
        from auto_cleanup_duplicates import auto_cleanup_duplicates
        auto_cleanup_duplicates()
    except Exception as e:
        print(f"⚠️ Auto-cleanup failed (non-critical): {e}")

# Include API routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(rootly.router, prefix="/rootly", tags=["rootly"])
app.include_router(pagerduty.router, prefix="/pagerduty", tags=["pagerduty"])
app.include_router(analysis.router, prefix="/analysis", tags=["analysis"])
app.include_router(analyses.router, prefix="/analyses", tags=["burnout-analyses"])
app.include_router(github.router, prefix="/integrations", tags=["github-integration"])
app.include_router(slack.router, prefix="/integrations", tags=["slack-integration"])
app.include_router(llm.router, tags=["llm-tokens"])
app.include_router(mappings.router, prefix="/integrations", tags=["integration-mappings"])
app.include_router(manual_mappings.router, prefix="/integrations", tags=["manual-mappings"])
app.include_router(debug.router, prefix="/api", tags=["debug"])
app.include_router(migration.router, prefix="/migration", tags=["database-migration"])