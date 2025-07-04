#!/usr/bin/env python3
"""
Export raw Rootly data for inspection
"""
import asyncio
import json
from datetime import datetime
from app.core.rootly_client import RootlyAPIClient

async def export_all_data():
    """Export users and incidents data to JSON files"""
    
    # You'll need to replace this with your actual Rootly token
    token = "rootly_e1d1dca04f0d2e9a2e08a7fcc7dde31477e0b2ef6d1107879aaa14ebe9839dec"
    
    client = RootlyAPIClient(token)
    
    try:
        print("🔄 Fetching data from Rootly...")
        
        # Collect all data
        data = await client.collect_analysis_data(days_back=30)
        
        if data:
            # Export users
            users_file = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(users_file, 'w') as f:
                json.dump(data.get('users', []), f, indent=2)
            print(f"✅ Users exported to: {users_file}")
            print(f"   Total users: {len(data.get('users', []))}")
            
            # Export incidents  
            incidents_file = f"incidents_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(incidents_file, 'w') as f:
                json.dump(data.get('incidents', []), f, indent=2)
            print(f"✅ Incidents exported to: {incidents_file}")
            print(f"   Total incidents: {len(data.get('incidents', []))}")
            
            # Export metadata
            metadata_file = f"metadata_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(metadata_file, 'w') as f:
                json.dump(data.get('collection_metadata', {}), f, indent=2)
            print(f"✅ Metadata exported to: {metadata_file}")
            
            # Show sample user
            users = data.get('users', [])
            if users:
                print(f"\n📋 Sample User:")
                sample_user = users[0]
                print(f"   ID: {sample_user.get('id')}")
                print(f"   Name: {sample_user.get('attributes', {}).get('full_name')}")
                print(f"   Email: {sample_user.get('attributes', {}).get('email')}")
                print(f"   Team: {sample_user.get('attributes', {}).get('full_name_with_team')}")
            
            # Show sample incident
            incidents = data.get('incidents', [])
            if incidents:
                print(f"\n🚨 Sample Incident:")
                sample_incident = incidents[0] 
                attrs = sample_incident.get('attributes', {})
                print(f"   ID: {sample_incident.get('id')}")
                print(f"   Title: {attrs.get('title', 'N/A')[:50]}...")
                print(f"   Status: {attrs.get('status')}")
                print(f"   Created: {attrs.get('created_at')}")
                
        else:
            print("❌ No data retrieved")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(export_all_data())