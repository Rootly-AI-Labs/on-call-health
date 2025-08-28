"""
FastAPI main application for Rootly Burnout Detector.
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from .models import create_tables
from .core.config import settings
from .core.rate_limiting import limiter, custom_rate_limit_exceeded_handler
from .middleware.security import security_middleware
from .api.endpoints import auth, rootly, analysis, analyses, pagerduty, github, slack, llm, mappings, manual_mappings, changelog, debug_mappings

# Create FastAPI application
app = FastAPI(
    title="Rootly Burnout Detector API",
    description="API for detecting burnout risk in engineering teams using Rootly incident data",
    version="1.0.0"
)

# Add rate limiting to the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_exceeded_handler)

# Add security middleware
app.middleware("http")(security_middleware)

# Configure CORS - Secure configuration
def get_cors_origins():
    """Get allowed CORS origins based on environment."""
    # Always allow the configured frontend URL
    origins = [settings.FRONTEND_URL]
    
    # Add common development ports for localhost
    if settings.FRONTEND_URL.startswith("http://localhost"):
        # Allow common Next.js development ports
        origins.extend([
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://localhost:3002"
        ])
    
    # TEMPORARY: Allow localhost for OAuth testing (remove after testing)
    if not any("localhost" in origin for origin in origins):
        origins.extend([
            "http://localhost:3000",
            "http://localhost:3001"
        ])
    
    # Add production domains if they exist
    production_frontend = os.getenv("PRODUCTION_FRONTEND_URL")
    if production_frontend:
        origins.append(production_frontend)
    
    # Add the production domain explicitly
    origins.extend([
        "https://www.oncallburnout.com",
        "https://oncallburnout.com"
    ])
    
    # Add Vercel preview URLs if in development/staging
    vercel_url = os.getenv("VERCEL_URL") 
    if vercel_url:
        origins.append(f"https://{vercel_url}")
    
    # Remove duplicates while preserving order
    origins = list(dict.fromkeys(origins))
    
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
app.include_router(debug_mappings.router, prefix="/api", tags=["debug"])
