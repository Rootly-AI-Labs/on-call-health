#!/usr/bin/env python3
"""
Assign PagerDuty incidents to users based on Rootly team data
This simulates realistic incident response patterns for burnout testing
"""

import requests
import json
import random
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# PagerDuty credentials
PD_API_TOKEN = "u+yU3VeLnT_d1HuYzDrg"
PD_SERVICE_ID = "PB02TQZ"

# Rootly API endpoint (you'll need to add your Rootly token)
ROOTLY_API_BASE = "https://api.rootly.com/v1"


class IncidentAssigner:
    def __init__(self, pd_token: str, rootly_token: str = None):
        self.pd_token = pd_token
        self.rootly_token = rootly_token
        self.pd_headers = {
            "Authorization": f"Token token={pd_token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json"
        }
        self.rootly_headers = {
            "Authorization": f"Bearer {rootly_token}",
            "Content-Type": "application/json"
        } if rootly_token else {}
    
    def get_pagerduty_users(self) -> List[Dict]:
        """Get all PagerDuty users"""
        response = requests.get(
            "https://api.pagerduty.com/users",
            headers=self.pd_headers
        )
        if response.status_code == 200:
            return response.json()["users"]
        print(f"Error fetching PD users: {response.status_code}")
        return []
    
    def get_rootly_users(self) -> List[Dict]:
        """Get users from Rootly API"""
        if not self.rootly_token:
            # Return mock data if no Rootly token provided
            return self.get_mock_rootly_users()
        
        response = requests.get(
            f"{ROOTLY_API_BASE}/users",
            headers=self.rootly_headers,
            params={"page[size]": 100}
        )
        if response.status_code == 200:
            return response.json()["data"]
        print(f"Error fetching Rootly users: {response.status_code}")
        return []
    
    def get_mock_rootly_users(self) -> List[Dict]:
        """Mock Rootly users for testing"""
        return [
            {"attributes": {"full_name": "Alice Chen", "email": "alice.chen@example.com"}},
            {"attributes": {"full_name": "Bob Smith", "email": "bob.smith@example.com"}},
            {"attributes": {"full_name": "Charlie Davis", "email": "charlie.davis@example.com"}},
            {"attributes": {"full_name": "Diana Ross", "email": "diana.ross@example.com"}},
            {"attributes": {"full_name": "Eve Johnson", "email": "eve.johnson@example.com"}},
        ]
    
    def map_users(self, rootly_users: List[Dict], pd_users: List[Dict]) -> Dict[str, str]:
        """Map Rootly users to PagerDuty users by email"""
        user_map = {}
        
        # Create email -> PD user ID map
        pd_email_map = {user["email"].lower(): user["id"] for user in pd_users}
        
        # Map Rootly users to PD users
        for rootly_user in rootly_users:
            attrs = rootly_user.get("attributes", {})
            email = attrs.get("email", "").lower()
            name = attrs.get("full_name", attrs.get("name", "Unknown"))
            
            if email in pd_email_map:
                user_map[name] = pd_email_map[email]
                print(f"✓ Mapped {name} ({email}) to PagerDuty user {pd_email_map[email]}")
            else:
                print(f"✗ No PagerDuty user found for {name} ({email})")
        
        return user_map
    
    def get_open_incidents(self) -> List[Dict]:
        """Get open incidents from PagerDuty"""
        response = requests.get(
            "https://api.pagerduty.com/incidents",
            headers=self.pd_headers,
            params={
                "statuses[]": ["triggered", "acknowledged"],
                "service_ids[]": [PD_SERVICE_ID],
                "limit": 100
            }
        )
        if response.status_code == 200:
            return response.json()["incidents"]
        print(f"Error fetching incidents: {response.status_code}")
        return []
    
    def assign_incident(self, incident_id: str, user_id: str, from_user_id: str = None) -> bool:
        """Assign an incident to a user"""
        data = {
            "incident": {
                "type": "incident",
                "assignments": [{
                    "assignee": {
                        "id": user_id,
                        "type": "user_reference"
                    }
                }]
            }
        }
        
        # Need to specify who is making the assignment
        headers = self.pd_headers.copy()
        if from_user_id:
            headers["From"] = from_user_id
        else:
            # Use the same user as assignee (self-assignment)
            headers["From"] = user_id
        
        response = requests.put(
            f"https://api.pagerduty.com/incidents/{incident_id}",
            headers=headers,
            json=data
        )
        
        return response.status_code == 200
    
    def acknowledge_incident(self, incident_id: str, user_id: str) -> bool:
        """Acknowledge an incident"""
        data = {
            "incident": {
                "type": "incident",
                "status": "acknowledged"
            }
        }
        
        headers = self.pd_headers.copy()
        headers["From"] = user_id
        
        response = requests.put(
            f"https://api.pagerduty.com/incidents/{incident_id}",
            headers=headers,
            json=data
        )
        
        return response.status_code == 200
    
    def resolve_incident(self, incident_id: str, user_id: str, resolution: str = "Resolved") -> bool:
        """Resolve an incident"""
        data = {
            "incident": {
                "type": "incident",
                "status": "resolved",
                "resolution": resolution
            }
        }
        
        headers = self.pd_headers.copy()
        headers["From"] = user_id
        
        response = requests.put(
            f"https://api.pagerduty.com/incidents/{incident_id}",
            headers=headers,
            json=data
        )
        
        return response.status_code == 200
    
    def simulate_incident_response(self, user_map: Dict[str, str], response_patterns: Dict = None):
        """Simulate realistic incident response patterns"""
        
        if not user_map:
            print("No users mapped. Please ensure users exist in both Rootly and PagerDuty with matching emails.")
            return
        
        # Default response patterns (who handles what percentage of incidents)
        if response_patterns is None:
            response_patterns = {
                "high_responders": 0.6,  # 60% handled by 20% of team (burnout risk)
                "normal_responders": 0.3,  # 30% handled by 60% of team
                "low_responders": 0.1     # 10% handled by 20% of team
            }
        
        # Get open incidents
        incidents = self.get_open_incidents()
        if not incidents:
            print("No open incidents found. Create some incidents first!")
            return
        
        print(f"\nFound {len(incidents)} open incidents")
        print("Simulating incident response patterns...")
        print("=" * 60)
        
        # Categorize users
        user_names = list(user_map.keys())
        num_users = len(user_names)
        
        high_responders = user_names[:int(num_users * 0.2)] or user_names[:1]
        low_responders = user_names[-int(num_users * 0.2):] or user_names[-1:]
        normal_responders = [u for u in user_names if u not in high_responders and u not in low_responders]
        
        print(f"\nHigh responders (burnout risk): {high_responders}")
        print(f"Normal responders: {normal_responders}")
        print(f"Low responders: {low_responders}")
        print("=" * 60)
        
        # Assign incidents
        for i, incident in enumerate(incidents):
            # Determine which group handles this incident
            rand = random.random()
            if rand < response_patterns["high_responders"]:
                responder_name = random.choice(high_responders)
            elif rand < response_patterns["high_responders"] + response_patterns["normal_responders"]:
                responder_name = random.choice(normal_responders) if normal_responders else random.choice(user_names)
            else:
                responder_name = random.choice(low_responders)
            
            responder_id = user_map[responder_name]
            
            print(f"\nIncident {i+1}/{len(incidents)}: {incident['title'][:50]}...")
            
            # Assign
            if self.assign_incident(incident["id"], responder_id):
                print(f"  ✓ Assigned to {responder_name}")
                
                # Acknowledge after a short delay
                time.sleep(1)
                if self.acknowledge_incident(incident["id"], responder_id):
                    print(f"  ✓ Acknowledged by {responder_name}")
                    
                    # Optionally resolve some incidents
                    if random.random() < 0.3:  # Resolve 30% immediately
                        time.sleep(2)
                        resolution = f"Issue resolved by {responder_name}. Root cause identified and fixed."
                        if self.resolve_incident(incident["id"], responder_id, resolution):
                            print(f"  ✓ Resolved by {responder_name}")
            else:
                print(f"  ✗ Failed to assign incident")
            
            time.sleep(0.5)  # Rate limiting
        
        print("\n" + "=" * 60)
        print("Incident response simulation complete!")
        print("\nThis creates a realistic pattern where:")
        print("- Some team members handle most incidents (burnout risk)")
        print("- Response times vary")
        print("- Some incidents remain unresolved")
        print("\nRun your burnout analysis to see the results!")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Assign PagerDuty incidents using Rootly team data")
    parser.add_argument("--rootly-token", help="Rootly API token (optional, uses mock data if not provided)")
    parser.add_argument("--list-users", action="store_true", help="List users from both systems")
    parser.add_argument("--simulate", action="store_true", help="Run incident response simulation")
    
    args = parser.parse_args()
    
    assigner = IncidentAssigner(PD_API_TOKEN, args.rootly_token)
    
    # Get users from both systems
    print("Fetching users...")
    rootly_users = assigner.get_rootly_users()
    pd_users = assigner.get_pagerduty_users()
    
    print(f"\nFound {len(rootly_users)} Rootly users")
    print(f"Found {len(pd_users)} PagerDuty users")
    
    # Map users
    user_map = assigner.map_users(rootly_users, pd_users)
    
    if args.list_users:
        print("\nUser Mapping:")
        print("=" * 60)
        for name, pd_id in user_map.items():
            print(f"{name} -> PagerDuty ID: {pd_id}")
    
    if args.simulate:
        assigner.simulate_incident_response(user_map)


if __name__ == "__main__":
    main()