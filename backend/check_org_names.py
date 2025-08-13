#!/usr/bin/env python3
"""
Check what organization names are currently in the database.
"""

import os
import sys
import json
from sqlalchemy import create_engine, text

def check_organization_names(database_url):
    """Check current organization names in analyses."""
    
    if not database_url:
        print("❌ DATABASE_URL required")
        return
    
    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Get all analyses and their organization names
            result = conn.execute(text("""
                SELECT 
                    id, 
                    results->'metadata'->>'organization_name' as org_name,
                    config->'beta_integration_id' as beta_id,
                    created_at
                FROM analyses 
                WHERE results IS NOT NULL
                ORDER BY created_at DESC
                LIMIT 20
            """))
            
            analyses = result.fetchall()
            print(f"📊 Found {len(analyses)} recent analyses:")
            print()
            
            for analysis in analyses:
                analysis_id = analysis[0]
                org_name = analysis[1] or 'NULL'
                beta_id = analysis[2] 
                created_at = analysis[3]
                
                print(f"ID {analysis_id}: '{org_name}' (beta: {beta_id}) - {created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # Get summary counts
            print("\n📊 Organization name summary:")
            summary_result = conn.execute(text("""
                SELECT 
                    COALESCE(results->'metadata'->>'organization_name', 'NULL') as org_name,
                    COUNT(*) as count
                FROM analyses 
                WHERE results IS NOT NULL
                GROUP BY results->'metadata'->>'organization_name'
                ORDER BY count DESC
            """))
            
            for row in summary_result:
                org_name = row[0]
                count = row[1]
                print(f"  {org_name}: {count} analyses")
                
            # Check specifically for null values
            print("\n🔍 Checking for NULL organization names:")
            null_result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM analyses 
                WHERE results IS NOT NULL 
                AND (results->'metadata'->>'organization_name' IS NULL 
                     OR results->'metadata'->>'organization_name' = 'null')
            """))
            
            null_count = null_result.fetchone()[0]
            print(f"  Found {null_count} analyses with NULL organization names")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    database_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DATABASE_URL')
    check_organization_names(database_url)