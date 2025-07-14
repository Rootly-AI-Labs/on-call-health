#!/usr/bin/env python3
"""
Check test.db database for actual data
"""

import sqlite3
import json
from pathlib import Path

# Database paths
db_paths = ["test.db", "app.db"]

def check_database(db_name):
    db_path = Path(db_name)
    if not db_path.exists():
        print(f"❌ Database file {db_name} not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"🔍 Checking {db_name}...\n")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f"📋 Tables in {db_name}: {table_names}\n")
        
        # Check key tables
        key_tables = ['users', 'rootly_integrations', 'pagerduty_integrations', 'github_integrations', 'slack_integrations', 'analyses']
        
        for table_name in key_tables:
            if table_name in table_names:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"📊 {table_name}: {count} rows")
                
                # Show sample data if any exists
                if count > 0:
                    if table_name == 'users':
                        cursor.execute(f"SELECT id, email, rootly_user_id FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f"   User: ID={row[0]}, Email={row[1]}, Rootly ID={row[2]}")
                    elif table_name == 'rootly_integrations':
                        cursor.execute(f"SELECT id, user_id, organization_name, rootly_url FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f"   Rootly: ID={row[0]}, User={row[1]}, Org={row[2]}, URL={row[3]}")
                    elif table_name == 'pagerduty_integrations':
                        cursor.execute(f"SELECT id, user_id, created_at FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f"   PagerDuty: ID={row[0]}, User={row[1]}, Created={row[2]}")
                    elif table_name == 'github_integrations':
                        cursor.execute(f"SELECT id, user_id, github_username FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f"   GitHub: ID={row[0]}, User={row[1]}, Username={row[2]}")
                    elif table_name == 'slack_integrations':
                        cursor.execute(f"SELECT id, user_id, workspace_id FROM {table_name} LIMIT 3")
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f"   Slack: ID={row[0]}, User={row[1]}, Workspace={row[2]}")
                    elif table_name == 'analyses':
                        cursor.execute(f"SELECT id, user_id, status, created_at FROM {table_name} ORDER BY created_at DESC LIMIT 3")
                        rows = cursor.fetchall()
                        for row in rows:
                            print(f"   Analysis: ID={row[0]}, User={row[1]}, Status={row[2]}, Created={row[3]}")
            else:
                print(f"❌ {table_name}: table not found")
        
        print()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking {db_name}: {e}")

if __name__ == "__main__":
    for db in db_paths:
        check_database(db)
        print("-" * 50)