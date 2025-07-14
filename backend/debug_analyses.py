#!/usr/bin/env python3
"""
Debug analyses API to see what's happening with historical events
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.models.base import SessionLocal
from sqlalchemy import text
from datetime import datetime

def debug_analyses():
    print("🔍 Debugging analyses data...\n")
    
    try:
        with SessionLocal() as db:
            # Check all analyses
            result = db.execute(text("SELECT COUNT(*) FROM analyses")).fetchone()
            total_analyses = result[0]
            print(f"📊 Total analyses in database: {total_analyses}")
            
            if total_analyses > 0:
                # Get recent analyses
                result = db.execute(text("""
                    SELECT id, user_id, status, created_at, completed_at, rootly_integration_id 
                    FROM analyses 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)).fetchall()
                
                print(f"\n📋 Recent analyses:")
                for analysis in result:
                    print(f"   - ID: {analysis[0]}, User: {analysis[1]}, Status: {analysis[2]}")
                    print(f"     Created: {analysis[3]}, Completed: {analysis[4]}")
                    print(f"     Integration ID: {analysis[5]}")
                
                # Check analyses by user
                result = db.execute(text("""
                    SELECT user_id, COUNT(*) as count, 
                           MAX(created_at) as latest
                    FROM analyses 
                    GROUP BY user_id 
                    ORDER BY count DESC
                """)).fetchall()
                
                print(f"\n👤 Analyses by user:")
                for user_data in result:
                    print(f"   - User {user_data[0]}: {user_data[1]} analyses, latest: {user_data[2]}")
                
                # Check status distribution
                result = db.execute(text("""
                    SELECT status, COUNT(*) as count
                    FROM analyses 
                    GROUP BY status
                """)).fetchall()
                
                print(f"\n📈 Status distribution:")
                for status_data in result:
                    print(f"   - {status_data[0]}: {status_data[1]} analyses")
                    
                # Check if there are completed analyses
                result = db.execute(text("""
                    SELECT id, user_id, created_at, completed_at,
                           CASE WHEN results IS NOT NULL THEN 'Has Results' ELSE 'No Results' END as has_results
                    FROM analyses 
                    WHERE status = 'completed'
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)).fetchall()
                
                print(f"\n✅ Completed analyses:")
                if result:
                    for analysis in result:
                        print(f"   - ID: {analysis[0]}, User: {analysis[1]}")
                        print(f"     Created: {analysis[2]}, Completed: {analysis[3]}")
                        print(f"     Results: {analysis[4]}")
                else:
                    print("   - No completed analyses found")
            
            # Check users for context
            result = db.execute(text("SELECT id, email FROM users")).fetchall()
            print(f"\n👥 Users in system:")
            for user in result:
                print(f"   - ID: {user[0]}, Email: {user[1]}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_analyses()