#!/usr/bin/env python3
"""
Check integrations in the database to see what's currently stored
"""

import sqlite3
import json
from pathlib import Path

# Database path
db_path = Path("app.db")

def check_integrations():
    if not db_path.exists():
        print("❌ Database file app.db not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking integrations in database...\n")
        
        # Check all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"📋 Available tables: {[table[0] for table in tables]}\n")
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👤 Total users: {user_count}")
        
        if user_count > 0:
            cursor.execute("SELECT id, email, rootly_user_id FROM users LIMIT 5")
            users = cursor.fetchall()
            print("   Recent users:")
            for user in users:
                print(f"   - ID: {user[0]}, Email: {user[1]}, Rootly ID: {user[2]}")
        
        print()
        
        # Check Rootly integrations
        cursor.execute("SELECT COUNT(*) FROM rootly_integrations")
        rootly_count = cursor.fetchone()[0]
        print(f"🔧 Rootly integrations: {rootly_count}")
        
        if rootly_count > 0:
            cursor.execute("SELECT id, user_id, rootly_url, organization_name, created_at FROM rootly_integrations")
            rootly_integrations = cursor.fetchall()
            for integration in rootly_integrations:
                print(f"   - ID: {integration[0]}, User: {integration[1]}, URL: {integration[2]}, Org: {integration[3]}, Created: {integration[4]}")
        
        print()
        
        # Check PagerDuty integrations
        cursor.execute("SELECT COUNT(*) FROM pagerduty_integrations")
        pd_count = cursor.fetchone()[0]
        print(f"📟 PagerDuty integrations: {pd_count}")
        
        if pd_count > 0:
            cursor.execute("SELECT id, user_id, integration_key, created_at FROM pagerduty_integrations")
            pd_integrations = cursor.fetchall()
            for integration in pd_integrations:
                print(f"   - ID: {integration[0]}, User: {integration[1]}, Key: {integration[2][:10]}..., Created: {integration[3]}")
        
        print()
        
        # Check GitHub integrations
        try:
            cursor.execute("SELECT COUNT(*) FROM github_integrations")
            github_count = cursor.fetchone()[0]
            print(f"🐙 GitHub integrations: {github_count}")
            
            if github_count > 0:
                cursor.execute("SELECT id, user_id, github_username, created_at FROM github_integrations")
                github_integrations = cursor.fetchall()
                for integration in github_integrations:
                    print(f"   - ID: {integration[0]}, User: {integration[1]}, Username: {integration[2]}, Created: {integration[3]}")
        except sqlite3.OperationalError:
            print("🐙 GitHub integrations table doesn't exist")
        
        print()
        
        # Check Slack integrations
        try:
            cursor.execute("SELECT COUNT(*) FROM slack_integrations")
            slack_count = cursor.fetchone()[0]
            print(f"💬 Slack integrations: {slack_count}")
            
            if slack_count > 0:
                cursor.execute("SELECT id, user_id, webhook_url, created_at FROM slack_integrations")
                slack_integrations = cursor.fetchall()
                for integration in slack_integrations:
                    webhook_preview = integration[2][:30] + "..." if len(integration[2]) > 30 else integration[2]
                    print(f"   - ID: {integration[0]}, User: {integration[1]}, Webhook: {webhook_preview}, Created: {integration[3]}")
        except sqlite3.OperationalError:
            print("💬 Slack integrations table doesn't exist")
        
        print()
        
        # Check analyses
        try:
            cursor.execute("SELECT COUNT(*) FROM analyses")
            analysis_count = cursor.fetchone()[0]
            print(f"📊 Analyses: {analysis_count}")
            
            if analysis_count > 0:
                cursor.execute("SELECT id, user_id, status, created_at FROM analyses ORDER BY created_at DESC LIMIT 5")
                analyses = cursor.fetchall()
                print("   Recent analyses:")
                for analysis in analyses:
                    print(f"   - ID: {analysis[0]}, User: {analysis[1]}, Status: {analysis[2]}, Created: {analysis[3]}")
        except sqlite3.OperationalError:
            print("📊 Analyses table doesn't exist")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    check_integrations()