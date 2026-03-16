#!/usr/bin/env python3
"""Export the OpenAPI spec from the FastAPI app without starting the server.

Usage:
    cd backend && python -m scripts.export_openapi
    # or
    cd backend && python scripts/export_openapi.py
"""
import json
import os
import sys

# Minimal env vars so the app module can be imported without a real DB
os.environ.setdefault("DATABASE_URL", "sqlite:///dummy.db")
os.environ.setdefault("JWT_SECRET_KEY", "dummy")
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ.setdefault("LOG_LEVEL", "ERROR")

# Ensure the backend package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

OUTPUT = os.path.join(os.path.dirname(__file__), "..", "openapi.json")

spec = app.openapi()
with open(OUTPUT, "w") as f:
    json.dump(spec, f, indent=2)

print(f"Exported {len(spec['paths'])} paths to {os.path.abspath(OUTPUT)}")
