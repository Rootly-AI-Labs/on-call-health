#!/usr/bin/env python3
"""
Check what's actually in the database
"""

import sqlite3
import json
from pathlib import Path

# Database path
db_path = Path("app.db")

def check_database():
    if not db_path.exists():
        print("❌ Database file app.db not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking actual database content...\n")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f"📋 All tables: {table_names}\n")
        
        # Check each table
        for table_name in table_names:
            if table_name.startswith('sqlite_'):
                continue
                
            print(f"📊 Table: {table_name}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"   Columns: {[col[1] for col in columns]}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   Row count: {count}")
            
            # Show sample data if any exists
            if count > 0 and count <= 10:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                print(f"   Sample data:")
                for i, row in enumerate(rows):
                    print(f"     Row {i+1}: {row}")
            elif count > 10:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print(f"   First 3 rows:")
                for i, row in enumerate(rows):
                    print(f"     Row {i+1}: {row}")
            
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")

if __name__ == "__main__":
    check_database()