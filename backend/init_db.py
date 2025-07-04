#!/usr/bin/env python3
"""
Database initialization script for Rootly Burnout Detector
"""

import sys
import os

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.base import Base, engine, create_tables

def main():
    print("Creating database tables...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("Database tables created successfully!")
    
    # Verify tables were created
    from sqlalchemy import text
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = result.fetchall()
        print(f"Tables created: {[table[0] for table in tables]}")

if __name__ == "__main__":
    main()