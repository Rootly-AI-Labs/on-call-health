#!/usr/bin/env python3
"""
Update historical analyses to use the same real organization names as the latest analyses.
Run this after creating a new analysis that has the real org name.
"""

import os
import sys
import json
from sqlalchemy import create_engine, text

def update_historical_with_real_names(database_url):
    """Update historical analyses to use real organization names from latest analyses."""
    
    if not database_url:
        print("❌ DATABASE_URL required")
        return
    
    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # First, get the real organization names from the most recent analyses
            print("🔍 Getting real organization names from recent analyses...")
            
            recent_result = conn.execute(text("""
                SELECT DISTINCT 
                    config->'beta_integration_id' as beta_id,
                    results->'metadata'->>'organization_name' as org_name
                FROM analyses 
                WHERE results IS NOT NULL 
                AND config IS NOT NULL
                AND config->'beta_integration_id' IS NOT NULL
                AND results->'metadata'->>'organization_name' NOT IN ('Beta Organization', 'Rootly', 'PagerDuty', 'Organization')
                ORDER BY id DESC
                LIMIT 10
            """))
            
            real_org_names = {}
            for row in recent_result:
                beta_id = row[0]  # e.g., "beta-rootly" 
                org_name = row[1]  # e.g., "Acme Corp"
                if beta_id and org_name:
                    beta_id_clean = beta_id.strip('"')  # Remove JSON quotes
                    real_org_names[beta_id_clean] = org_name
                    print(f"   Found: {beta_id_clean} -> '{org_name}'")
            
            if not real_org_names:
                print("❌ No recent analyses found with real organization names.")
                print("    Please run a new analysis first to get the real organization names from APIs.")
                return False
            
            # Now update historical analyses that have generic names
            print(f"\n🔧 Updating historical analyses...")
            
            for beta_id, real_name in real_org_names.items():
                # Update analyses with generic names to use the real name
                update_result = conn.execute(text("""
                    UPDATE analyses 
                    SET results = jsonb_set(
                        results, 
                        '{metadata,organization_name}', 
                        to_jsonb(:real_name::text)
                    )
                    WHERE results IS NOT NULL 
                    AND config IS NOT NULL
                    AND config->'beta_integration_id' = to_jsonb(:beta_id::text)
                    AND results->'metadata'->>'organization_name' IN ('Beta Organization', 'Rootly', 'PagerDuty')
                """), {
                    'real_name': real_name,
                    'beta_id': beta_id
                })
                
                updated_count = update_result.rowcount
                if updated_count > 0:
                    print(f"   Updated {updated_count} {beta_id} analyses to '{real_name}'")
            
            # Commit all changes
            conn.commit()
            print(f"\n✅ Historical update complete!")
            
            # Show summary of current state
            print(f"\n📊 Current organization name distribution:")
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
                print(f"   {org_name}: {count} analyses")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    database_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DATABASE_URL')
    success = update_historical_with_real_names(database_url)
    sys.exit(0 if success else 1)