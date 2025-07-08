#!/usr/bin/env python3
"""
Quick script to create PagerDuty incidents
Run this directly: python3 quick_create_incidents.py
"""

import requests
import json
import time
from datetime import datetime

# Your PagerDuty credentials
PD_API_TOKEN = "u+yU3VeLnT_d1HuYzDrg"
PD_SERVICE_ID = "PB02TQZ"

# Headers for API requests
headers = {
    "Authorization": f"Token token={PD_API_TOKEN}",
    "Accept": "application/vnd.pagerduty+json;version=2",
    "Content-Type": "application/json"
}

# Team members with burnout patterns (simulated)
team_members = [
    {"name": "Alex Chen", "risk": "high", "incidents": 40},
    {"name": "Sarah Johnson", "risk": "high", "incidents": 35},
    {"name": "Mike Williams", "risk": "medium", "incidents": 15},
    {"name": "Emma Davis", "risk": "low", "incidents": 10},
]

# Incident templates
incidents = [
    {"title": "[PROD] Database connection pool exhausted", "urgency": "high"},
    {"title": "[CRITICAL] API Gateway returning 503 errors", "urgency": "high"},
    {"title": "[ALERT] Memory leak detected - 95% RAM", "urgency": "high"},
    {"title": "[AFTER-HOURS] Payment service down", "urgency": "high"},
    {"title": "[WEEKEND] Backup job failed", "urgency": "low"},
    {"title": "[WARN] Disk usage at 85%", "urgency": "low"},
    {"title": "[PROD] Cache hit rate dropped", "urgency": "low"},
    {"title": "[STAGING] Deploy pipeline blocked", "urgency": "low"},
]

print("🚀 Creating PagerDuty incidents with burnout patterns...")
print("=" * 60)

created_count = 0

for incident_data in incidents:
    # Assign based on risk level
    if incident_data["urgency"] == "high":
        # High urgency goes to high-risk users
        assigned_to = team_members[0]["name"] if created_count % 2 == 0 else team_members[1]["name"]
    else:
        # Low urgency distributed more evenly
        assigned_to = team_members[created_count % 4]["name"]
    
    # Create incident
    body = {
        "incident": {
            "type": "incident",
            "title": incident_data["title"],
            "service": {
                "id": PD_SERVICE_ID,
                "type": "service_reference"
            },
            "urgency": incident_data["urgency"],
            "body": {
                "type": "incident_body",
                "details": f"Test incident assigned to {assigned_to} for burnout pattern simulation"
            }
        }
    }
    
    try:
        response = requests.post(
            "https://api.pagerduty.com/incidents",
            headers=headers,
            json=body
        )
        
        if response.status_code == 201:
            incident = response.json()["incident"]
            created_count += 1
            print(f"✓ Created: {incident_data['title'][:40]}... → {assigned_to}")
            
            # Add note about assignment
            note_body = {
                "note": {
                    "content": f"Handled by: {assigned_to}"
                }
            }
            requests.post(
                f"https://api.pagerduty.com/incidents/{incident['id']}/notes",
                headers=headers,
                json=note_body
            )
        else:
            print(f"✗ Failed: {response.status_code} - {response.text[:100]}")
    
    except Exception as e:
        print(f"✗ Error: {e}")
    
    time.sleep(1)  # Rate limiting

print("\n" + "=" * 60)
print(f"✅ Created {created_count} incidents")
print("\n📊 Pattern created:")
print("  - Alex & Sarah: Most high-urgency incidents (burnout risk)")
print("  - Mike: Some incidents (medium risk)")
print("  - Emma: Few incidents (low risk)")
print("\n💡 Run burnout analysis in Rootly to see these patterns!")