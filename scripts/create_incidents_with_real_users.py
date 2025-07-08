#!/usr/bin/env python3
"""
Create PagerDuty incidents and properly assign them to real users
"""

import requests
import json
import time
import random
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

def get_pagerduty_users():
    """Get all PagerDuty users in the account"""
    response = requests.get(
        "https://api.pagerduty.com/users",
        headers=headers
    )
    
    if response.status_code == 200:
        users = response.json()["users"]
        print(f"Found {len(users)} PagerDuty users:")
        for user in users:
            print(f"  - {user['name']} ({user['email']}) - ID: {user['id']}")
        return users
    else:
        print(f"Error fetching users: {response.status_code}")
        return []

def create_and_assign_incident(title, urgency, user_id, user_name):
    """Create an incident and assign it to a specific user"""
    
    # Create incident with assignment
    body = {
        "incident": {
            "type": "incident",
            "title": title,
            "service": {
                "id": PD_SERVICE_ID,
                "type": "service_reference"
            },
            "urgency": urgency,
            "body": {
                "type": "incident_body",
                "details": f"Test incident for burnout simulation - Assigned to {user_name}"
            },
            "assignments": [{
                "assignee": {
                    "id": user_id,
                    "type": "user_reference"
                }
            }]
        }
    }
    
    response = requests.post(
        "https://api.pagerduty.com/incidents",
        headers=headers,
        json=body
    )
    
    if response.status_code == 201:
        return response.json()["incident"]
    else:
        print(f"Error creating incident: {response.status_code} - {response.text}")
        return None

def simulate_burnout_with_real_users():
    """Create incidents with burnout patterns using real users"""
    
    # Get real users
    users = get_pagerduty_users()
    
    if not users:
        print("No users found!")
        return
    
    print("\n" + "=" * 60)
    print("🔥 Creating Burnout Pattern Simulation")
    print("=" * 60)
    
    # If only one user, we'll create different patterns with notes
    if len(users) == 1:
        print(f"\nOnly one user found: {users[0]['name']}")
        print("Creating incidents with notes to simulate different team members...")
        
        # Simulated team members
        simulated_team = [
            {"name": "Alex Chen (High Risk)", "incidents": 5, "pattern": "after-hours"},
            {"name": "Sarah Johnson (High Risk)", "incidents": 4, "pattern": "critical"},
            {"name": "Mike Williams (Medium Risk)", "incidents": 2, "pattern": "normal"},
            {"name": "Emma Davis (Low Risk)", "incidents": 1, "pattern": "normal"}
        ]
        
        user = users[0]
        created_count = 0
        
        for team_member in simulated_team:
            for i in range(team_member["incidents"]):
                # Create incident title based on pattern
                if team_member["pattern"] == "after-hours":
                    title = f"[AFTER-HOURS] System alert - {datetime.now().strftime('%H:%M')}"
                    urgency = "high"
                elif team_member["pattern"] == "critical":
                    title = f"[CRITICAL] Production issue #{random.randint(100,999)}"
                    urgency = "high"
                else:
                    title = f"[WARN] Monitoring alert #{random.randint(100,999)}"
                    urgency = "low"
                
                # Create incident
                incident = create_and_assign_incident(
                    title=f"{title} - Handled by {team_member['name']}",
                    urgency=urgency,
                    user_id=user["id"],
                    user_name=user["name"]
                )
                
                if incident:
                    created_count += 1
                    print(f"✓ Created: {title} → Simulated handler: {team_member['name']}")
                    
                    # Add detailed note about the simulated handler
                    note_body = {
                        "note": {
                            "content": (f"For burnout simulation:\n"
                                      f"Handled by: {team_member['name']}\n"
                                      f"This represents a {team_member['pattern']} incident pattern")
                        }
                    }
                    requests.post(
                        f"https://api.pagerduty.com/incidents/{incident['id']}/notes",
                        headers=headers,
                        json=note_body
                    )
                
                time.sleep(1)
        
    else:
        # Multiple users - distribute incidents to create burnout pattern
        print(f"\nFound {len(users)} users. Creating burnout pattern distribution...")
        
        # Assign roles to users (first user gets most incidents)
        high_risk_user = users[0]
        other_users = users[1:] if len(users) > 1 else []
        
        print(f"\nSimulated pattern:")
        print(f"  High risk: {high_risk_user['name']} (will get 70% of incidents)")
        for user in other_users:
            print(f"  Normal: {user['name']} (will get fewer incidents)")
        
        # Create incidents
        incident_templates = [
            {"title": "[CRITICAL] Database down", "urgency": "high"},
            {"title": "[PROD] API errors spiking", "urgency": "high"},
            {"title": "[AFTER-HOURS] Memory leak detected", "urgency": "high"},
            {"title": "[CRITICAL] Payment service failure", "urgency": "high"},
            {"title": "[WEEKEND] Backup failed", "urgency": "low"},
            {"title": "[WARN] Disk space low", "urgency": "low"},
            {"title": "[INFO] SSL cert expiring", "urgency": "low"},
            {"title": "[PROD] Cache errors", "urgency": "low"},
        ]
        
        created_count = 0
        
        for incident_data in incident_templates:
            # 70% chance to assign to high-risk user
            if random.random() < 0.7 or not other_users:
                assigned_user = high_risk_user
            else:
                assigned_user = random.choice(other_users)
            
            incident = create_and_assign_incident(
                title=incident_data["title"],
                urgency=incident_data["urgency"],
                user_id=assigned_user["id"],
                user_name=assigned_user["name"]
            )
            
            if incident:
                created_count += 1
                print(f"✓ Created: {incident_data['title']} → {assigned_user['name']}")
            
            time.sleep(1)
    
    print("\n" + "=" * 60)
    print(f"✅ Created {created_count} incidents")
    print("\n📊 What this simulates:")
    print("  - Uneven distribution (burnout indicator)")
    print("  - After-hours incidents")
    print("  - Critical incidents handled by same person")
    print("\n💡 Check the incidents in PagerDuty to see the pattern!")

if __name__ == "__main__":
    simulate_burnout_with_real_users()