#!/usr/bin/env python3
"""
Quick check for analysis ID 64 and any analysis with 273 incidents.
"""

import os
import sys
import json
import sqlite3
from datetime import datetime

def check_sqlite_database():
    """Check SQLite database for analysis ID 64."""
    db_paths = [
        'app.db',
        'test.db', 
        'burnout_analysis.db',
        '../app.db',
        '../test.db'
    ]
    
    for db_path in db_paths:
        if os.path.exists(db_path):
            print(f"Checking database: {db_path}")
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check for analysis ID 64
                cursor.execute("SELECT id, status, created_at, results FROM analyses WHERE id = 64")
                result = cursor.fetchone()
                
                if result:
                    print(f"✅ FOUND Analysis ID 64 in {db_path}")
                    print(f"   Status: {result[1]}")
                    print(f"   Created: {result[2]}")
                    
                    if result[3]:  # results field
                        try:
                            results = json.loads(result[3])
                            total_incidents = results.get('metadata', {}).get('total_incidents', 0)
                            daily_trends = len(results.get('daily_trends', []))
                            print(f"   Total Incidents: {total_incidents}")
                            print(f"   Daily Trends: {daily_trends} days")
                            
                            if total_incidents == 273:
                                print("   🎯 MATCH: This has 273 incidents!")
                            
                        except Exception as e:
                            print(f"   Error parsing results: {e}")
                else:
                    print(f"❌ Analysis ID 64 NOT FOUND in {db_path}")
                
                # Look for any analysis with 273 incidents
                cursor.execute("""
                    SELECT id, status, created_at, results 
                    FROM analyses 
                    WHERE results LIKE '%"total_incidents": 273%' 
                    OR results LIKE '%"total_incidents":273%'
                    ORDER BY created_at DESC
                """)
                
                matches = cursor.fetchall()
                if matches:
                    print(f"\n🔍 Found {len(matches)} analyses with 273 incidents:")
                    for match in matches:
                        print(f"   ID: {match[0]}, Status: {match[1]}, Created: {match[2]}")
                
                # Get most recent analyses
                cursor.execute("""
                    SELECT id, status, created_at, results 
                    FROM analyses 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """)
                
                recent = cursor.fetchall()
                print(f"\n📋 Most Recent Analyses in {db_path}:")
                for r in recent:
                    if r[3]:
                        try:
                            results = json.loads(r[3])
                            incidents = results.get('metadata', {}).get('total_incidents', 0)
                            print(f"   ID: {r[0]}, Status: {r[1]}, Incidents: {incidents}, Created: {r[2]}")
                        except:
                            print(f"   ID: {r[0]}, Status: {r[1]}, Created: {r[2]} (parse error)")
                    else:
                        print(f"   ID: {r[0]}, Status: {r[1]}, Created: {r[2]} (no results)")
                
                conn.close()
                print()
                
            except Exception as e:
                print(f"Error checking {db_path}: {e}")
        else:
            print(f"Database not found: {db_path}")

def main():
    print("=== Checking for Analysis ID 64 and 273 Incidents ===\n")
    check_sqlite_database()

if __name__ == "__main__":
    main()