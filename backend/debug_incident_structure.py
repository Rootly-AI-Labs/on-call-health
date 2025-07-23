#!/usr/bin/env python3

import asyncio
import os
import json
import sqlite3
from app.core.pagerduty_client import PagerDutyAPIClient
from datetime import datetime, timedelta

async def main():
    # Get API token from database
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT api_token FROM rootly_integrations 
        WHERE platform = 'pagerduty' AND user_id = 2
        ORDER BY created_at DESC 
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        print("Error: No PagerDuty integration found")
        return
    
    api_token = result[0]
    
    # Create client
    client = PagerDutyAPIClient(api_token)
    
    # Get recent incidents
    since = datetime.now() - timedelta(days=30)
    incidents = await client.get_incidents(since=since, limit=50)
    
    print(f"Raw incidents count: {len(incidents)}")
    if incidents:
        print("\n=== Raw PagerDuty Incident Structure ===")
        print(json.dumps(incidents[0], indent=2, default=str)[:2000])
    
    # Test normalization
    users = await client.get_users(limit=100)
    normalized = client.normalize_to_common_format(incidents, users)
    
    print(f"\nNormalized incidents count: {len(normalized['incidents'])}")
    if normalized['incidents']:
        print("\n=== Normalized Incident Structure ===")
        print(json.dumps(normalized['incidents'][0], indent=2, default=str))
        
        # Show status breakdown
        status_counts = {}
        for incident in normalized['incidents']:
            status = incident.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n=== Status Breakdown ===")
        for status, count in status_counts.items():
            print(f"{status}: {count}")

if __name__ == "__main__":
    asyncio.run(main())