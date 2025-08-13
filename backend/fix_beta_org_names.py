#!/usr/bin/env python3
"""
Fix analyses that have 'Beta Organization' to show proper platform names.
"""

import os
import sys
import json
from sqlalchemy import create_engine, text

def fix_beta_organization_names(database_url):
    """Update analyses with 'Beta Organization' to use proper platform names."""
    
    if not database_url:
        print("❌ DATABASE_URL required")
        return
    
    print(f"🔗 Connecting to database...")
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Get analyses with 'Beta Organization' 
            result = conn.execute(text("""
                SELECT id, results, config, created_at 
                FROM analyses 
                WHERE results IS NOT NULL 
                AND results->'metadata'->>'organization_name' = 'Beta Organization'
                ORDER BY created_at DESC
            """))
            
            analyses = result.fetchall()
            print(f"📊 Found {len(analyses)} analyses with 'Beta Organization'")
            
            updated_count = 0
            
            for analysis in analyses:
                analysis_id = analysis[0]
                results = analysis[1] if isinstance(analysis[1], dict) else {}
                config = analysis[2] if isinstance(analysis[2], dict) else {}
                created_at = analysis[3]
                
                metadata = results.get('metadata', {})
                current_org_name = metadata.get('organization_name')
                
                if current_org_name == 'Beta Organization':
                    # Determine correct name based on config
                    beta_integration_id = config.get('beta_integration_id')
                    
                    if beta_integration_id == "beta-rootly":
                        new_org_name = "Rootly"
                    elif beta_integration_id == "beta-pagerduty":
                        new_org_name = "PagerDuty"
                    else:
                        new_org_name = "Organization"  # Generic fallback
                    
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
                print(f"✅ Updated {updated_count} analyses from 'Beta Organization' to proper platform names")
            else:
                print("ℹ️  No analyses needed updating")
                
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    database_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv('DATABASE_URL')
    success = fix_beta_organization_names(database_url)
    sys.exit(0 if success else 1)