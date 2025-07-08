#!/usr/bin/env python3
"""
Create test incidents for Rootly burnout testing
"""

import requests
import json
import time
import random
from datetime import datetime, timedelta

API_TOKEN = "u+yU3VeLnT_d1HuYzDrg"
SERVICE_ID = "PB02TQZ"

def create_incident(title, urgency="high", description=None):
    """Create a single incident"""
    
    headers = {
        "Authorization": f"Token token={API_TOKEN}",
        "Accept": "application/vnd.pagerduty+json;version=2",
        "Content-Type": "application/json"
    }
    
    incident_data = {
        "incident": {
            "type": "incident",
            "title": title,
            "service": {
                "id": SERVICE_ID,
                "type": "service_reference"
            },
            "urgency": urgency,
            "body": {
                "type": "incident_body",
                "details": description or f"Test incident created at {datetime.now()}"
            }
        }
    }
    
    response = requests.post(
        "https://api.pagerduty.com/incidents",
        headers=headers,
        json=incident_data
    )
    
    if response.status_code == 201:
        return response.json()["incident"]
    else:
        print(f"Error creating incident: {response.status_code} - {response.text}")
        return None


def create_realistic_test_set():
    """Create a realistic set of test incidents for burnout detection"""
    
    print("Creating test incidents for Rootly burnout detection...")
    print("=" * 60)
    
    # Incident templates
    incident_templates = [
        # High urgency - critical issues
        {"title": "[PROD] Database connection pool exhausted - affecting all services", "urgency": "high"},
        {"title": "[PROD] API Gateway returning 503 errors - 50% error rate", "urgency": "high"},
        {"title": "[CRITICAL] Payment processing service down", "urgency": "high"},
        {"title": "[PROD] Memory leak detected - server at 95% RAM usage", "urgency": "high"},
        {"title": "[CRITICAL] Main database replication lag > 5 minutes", "urgency": "high"},
        
        # Medium urgency - degraded performance
        {"title": "[WARN] API response times degraded - p95 > 2s", "urgency": "low"},
        {"title": "[WARN] Background job queue growing - 1000+ jobs pending", "urgency": "low"},
        {"title": "[STAGING] Deployment failed - rollback initiated", "urgency": "low"},
        {"title": "[WARN] Cache hit rate dropped to 60%", "urgency": "low"},
        {"title": "[WARN] Disk usage at 80% on prod-app-03", "urgency": "low"},
        
        # After-hours incidents (will create with timestamps)
        {"title": "[PROD] Spike in 500 errors detected - automated alert", "urgency": "high"},
        {"title": "[PROD] SSL certificate expiring in 24 hours", "urgency": "low"},
        {"title": "[CRITICAL] DDoS attack detected - rate limiting engaged", "urgency": "high"},
        
        # Weekend incidents
        {"title": "[PROD] Scheduled backup job failed", "urgency": "low"},
        {"title": "[PROD] Unusual login activity detected from new IP range", "urgency": "high"},
    ]
    
    created_incidents = []
    
    # Create incidents with varied patterns
    for i, template in enumerate(incident_templates):
        try:
            print(f"\nCreating incident {i+1}/{len(incident_templates)}:")
            print(f"  Title: {template['title']}")
            print(f"  Urgency: {template['urgency']}")
            
            incident = create_incident(
                title=template['title'],
                urgency=template['urgency'],
                description=f"Test incident for burnout detection analysis. Created as part of test data set."
            )
            
            if incident:
                created_incidents.append(incident)
                print(f"  ✓ Created: {incident['id']}")
            else:
                print(f"  ✗ Failed to create incident")
            
            # Small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print(f"Successfully created {len(created_incidents)} test incidents")
    print("\nIncident IDs:")
    for incident in created_incidents:
        print(f"  - {incident['id']}: {incident['title']}")
    
    return created_incidents


def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--custom":
        # Create a single custom incident
        if len(sys.argv) < 3:
            print("Usage: python script.py --custom 'Incident title'")
            return
            
        title = sys.argv[2]
        urgency = sys.argv[3] if len(sys.argv) > 3 else "high"
        
        print(f"Creating custom incident: {title}")
        incident = create_incident(title, urgency)
        if incident:
            print(f"✓ Created incident: {incident['id']}")
        else:
            print("✗ Failed to create incident")
    
    else:
        # Create the full test set
        create_realistic_test_set()
        
        print("\n" + "=" * 60)
        print("Next steps:")
        print("1. Wait a few minutes for incidents to appear in Rootly")
        print("2. Run the burnout analysis in your dashboard")
        print("3. Some incidents will appear as 'after-hours' based on your timezone")
        print("\nTo resolve these incidents later:")
        print("  - Go to PagerDuty and bulk resolve them")
        print("  - Or they'll auto-resolve based on your service settings")


if __name__ == "__main__":
    main()