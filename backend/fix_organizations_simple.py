#!/usr/bin/env python3
"""
Simple script to fix null organization names in historical analyses.
Run with: python fix_organizations_simple.py [DATABASE_URL]
"""

import os
import sys
import json
from sqlalchemy import create_engine, text, update

def fix_null_organizations(database_url):
    """Update analyses with null organization names using Railway tokens."""
    
    # For Railway production database
    if not database_url:
        print("❌ DATABASE_URL required")
        print("Usage: python fix_organizations_simple.py [DATABASE_URL]")
        return
    
    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Get analyses with null organization names (both NULL and 'null' string)
            result = conn.execute(text("""
                SELECT id, results, config, created_at 
                FROM analyses 
                WHERE results IS NOT NULL 
                AND (results->'metadata'->>'organization_name' IS NULL
                     OR results->'metadata'->>'organization_name' = 'null'
                     OR results->'metadata'->>'organization_name' = 'NULL')
                ORDER BY created_at DESC
            """))
            
            analyses = result.fetchall()
            print(f"📊 Found {len(analyses)} analyses with null organization names")
            
            updated_count = 0
            
            for analysis in analyses:
                analysis_id = analysis[0]
                results = analysis[1] if isinstance(analysis[1], dict) else (json.loads(analysis[1]) if analysis[1] else {})
                config = analysis[2] if isinstance(analysis[2], dict) else (json.loads(analysis[2]) if analysis[2] else {})
                created_at = analysis[3]
                
                metadata = results.get('metadata', {})
                current_org_name = metadata.get('organization_name')
                
                if current_org_name is None or current_org_name in ['null', 'NULL']:
                    # Determine organization name based on config
                    beta_integration_id = config.get('beta_integration_id')
                    
                    if beta_integration_id == "beta-rootly":
                        new_org_name = "Rootly"
                    elif beta_integration_id == "beta-pagerduty":
                        new_org_name = "PagerDuty"
                    else:
                        new_org_name = "Organization"
                    
                    print(f"🔧 Fixing analysis {analysis_id} ({created_at.strftime('%Y-%m-%d %H:%M')}) -> '{new_org_name}'")
                    
                    # Update the organization name
                    metadata['organization_name'] = new_org_name
                    results['metadata'] = metadata
                    
                    # Update in database
                    conn.execute(text("""
                        UPDATE analyses 
                        SET results = :results 
                        WHERE id = :analysis_id
                    """), {
                        'results': json.dumps(results),
                        'analysis_id': analysis_id
                    })
                    
                    updated_count += 1
            
            # Commit changes
            conn.commit()
            
            if updated_count > 0:
                print(f"✅ Updated {updated_count} analyses with proper organization names")
                
                # Show summary
                summary_result = conn.execute(text("""
                    SELECT 
                        results->'metadata'->>'organization_name' as org_name,
                        COUNT(*) as count
                    FROM analyses 
                    WHERE results IS NOT NULL
                    GROUP BY results->'metadata'->>'organization_name'
                    ORDER BY count DESC
                """))
                
                print("\n📊 Organization name summary after update:")
                for row in summary_result:
                    org_name = row[0] or 'null'
                    count = row[1]
                    print(f"  {org_name}: {count} analyses")
                    
            else:
                print("ℹ️  No analyses needed updating")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    # Get database URL from command line or environment
    database_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DATABASE_URL')
    success = fix_null_organizations(database_url)
    sys.exit(0 if success else 1)