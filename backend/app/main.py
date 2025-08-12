"""
FastAPI main application for Rootly Burnout Detector.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import create_tables
from .core.config import settings
from .api.endpoints import auth, rootly, analysis, analyses, pagerduty, github, slack, llm, mappings, manual_mappings, changelog

# Create FastAPI application
app = FastAPI(
    title="Rootly Burnout Detector API",
    description="API for detecting burnout risk in engineering teams using Rootly incident data",
    version="1.0.0"
)

# Configure CORS - Secure configuration
def get_cors_origins():
    """Get allowed CORS origins based on environment."""
    # Always allow the configured frontend URL
    origins = [settings.FRONTEND_URL]
    
    # Add production domains if they exist
    production_frontend = os.getenv("PRODUCTION_FRONTEND_URL")
    if production_frontend:
        origins.append(production_frontend)
    
    # Add Vercel preview URLs if in development/staging
    vercel_url = os.getenv("VERCEL_URL") 
    if vercel_url:
        origins.append(f"https://{vercel_url}")
    
    # Log allowed origins for debugging
    print(f"🔒 CORS Security: Allowing origins: {origins}")
    
    return origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),  # Specific allowed origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With"
    ],  # Specific headers only
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
app.include_router(changelog.router, prefix="/api", tags=["changelog"])
