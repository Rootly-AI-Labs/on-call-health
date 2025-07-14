#!/usr/bin/env python3
"""
Test that the backend is connecting to the correct database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.base import SessionLocal, engine
from sqlalchemy import text

def test_database_connection():
    print(f"🔧 Configuration DATABASE_URL: {settings.DATABASE_URL}")
    print(f"🔧 Engine URL: {engine.url}")
    
    # Test database connection
    try:
        with SessionLocal() as db:
            # Get database file info
            result = db.execute(text("PRAGMA database_list")).fetchall()
            print(f"📋 Connected databases: {result}")
            
            # Count users
            try:
                result = db.execute(text("SELECT COUNT(*) FROM users")).fetchone()
                print(f"👤 Users count: {result[0]}")
                
                # Get sample user
                result = db.execute(text("SELECT id, email FROM users LIMIT 1")).fetchone()
                if result:
                    print(f"👤 Sample user: ID={result[0]}, Email={result[1]}")
            except Exception as e:
                print(f"❌ Error querying users: {e}")
            
            # Count rootly integrations
            try:
                result = db.execute(text("SELECT COUNT(*) FROM rootly_integrations")).fetchone()
                print(f"🔧 Rootly integrations count: {result[0]}")
                
                # Get sample integration
                result = db.execute(text("SELECT id, organization_name FROM rootly_integrations LIMIT 1")).fetchone()
                if result:
                    print(f"🔧 Sample org: ID={result[0]}, Name={result[1]}")
            except Exception as e:
                print(f"❌ Error querying rootly_integrations: {e}")
                
            # Count analyses
            try:
                result = db.execute(text("SELECT COUNT(*) FROM analyses")).fetchone()
                print(f"📊 Analyses count: {result[0]}")
            except Exception as e:
                print(f"❌ Error querying analyses: {e}")
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")

if __name__ == "__main__":
    test_database_connection()