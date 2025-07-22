#!/usr/bin/env python3
"""
Check test.db database structure and data in detail
"""

import sqlite3
import json
from pathlib import Path

def check_test_database():
    db_path = Path("test.db")
    if not db_path.exists():
        print("❌ Database file test.db not found!")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking test.db structure and data...\n")
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        print(f"📋 All tables: {table_names}\n")
        
        # Check each table structure and data
        for table_name in table_names:
            print(f"📊 Table: {table_name}")
            
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"   Columns: {[f'{col[1]} ({col[2]})' for col in columns]}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"   Row count: {count}")
            
            # Show sample data if any exists
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3")
                rows = cursor.fetchall()
                print(f"   Sample data:")
                for i, row in enumerate(rows):
                    print(f"     Row {i+1}: {row}")
            
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking test.db: {e}")

if __name__ == "__main__":
    check_test_database()