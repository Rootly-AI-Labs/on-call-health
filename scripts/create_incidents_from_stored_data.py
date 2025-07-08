#!/usr/bin/env python3
"""
Create PagerDuty incidents using user data from stored Rootly analyses
"""

import sqlite3
import json
import requests
import random
import time
from datetime import datetime
from typing import List, Dict, Optional

# PagerDuty credentials
PD_API_TOKEN = "u+yU3VeLnT_d1HuYzDrg"
PD_SERVICE_ID = "PB02TQZ"

class StoredDataIncidentCreator:
    def __init__(self, pd_token: str, db_path: str = "../backend/app.db"):
        self.pd_token = pd_token
        self.db_path = db_path
        self.pd_headers = {
            "Authorization": f"Token token={pd_token}",
            "Accept": "application/vnd.pagerduty+json;version=2", 
            "Content-Type": "application/json"
        }
        self.users_data = []
        
    def fetch_users_from_db(self) -> List[Dict]:
        """Extract user data from stored analysis results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get the most recent completed analysis
        cursor.execute("""
            SELECT results 
            FROM analyses 
            WHERE status = 'completed' 
            AND results IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        if not row or not row[0]:
            print("No completed analyses found in database")
            return []
        
        # Parse the JSON results
        try:
            results = json.loads(row[0])
            
            # Extract users from team_analysis
            users = []
            if 'team_analysis' in results and 'members' in results['team_analysis']:
                for member in results['team_analysis']['members']:
                    users.append({
                        'name': member.get('user_name', 'Unknown'),
                        'email': member.get('user_email', ''),
                        'burnout_score': member.get('burnout_score', 0),
                        'risk_level': member.get('risk_level', 'unknown'),
                        'incident_count': member.get('incident_count', 0),
                        'metrics': member.get('metrics', {})
                    })
                
                print(f"Found {len(users)} users from stored analysis")
                return users
            else:
                print("No team member data found in analysis results")
                return []
                
        except json.JSONDecodeError as e:
            print(f"Error parsing analysis results: {e}")
            return []
    
    def create_incident(self, title: str, urgency: str = "high", 
                       description: str = None, assigned_to: str = None) -> Optional[Dict]:
        """Create a PagerDuty incident"""
        
        incident_data = {
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
                    "details": description or f"Test incident created at {datetime.now()}"
                }
            }
        }
        
        response = requests.post(
            "https://api.pagerduty.com/incidents",
            headers=self.pd_headers,
            json=incident_data
        )
        
        if response.status_code == 201:
            incident = response.json()["incident"]
            
            # Add a note about assignment if provided
            if assigned_to:
                note_data = {
                    "note": {
                        "content": f"Assigned to: {assigned_to}"
                    }
                }
                requests.post(
                    f"https://api.pagerduty.com/incidents/{incident['id']}/notes",
                    headers=self.pd_headers,
                    json=note_data
                )
            
            return incident
        else:
            print(f"Error creating incident: {response.status_code} - {response.text}")
            return None
    
    def simulate_realistic_burnout_pattern(self):
        """Create incidents based on actual burnout patterns from stored data"""
        
        # Fetch users from database
        users = self.fetch_users_from_db()
        
        if not users:
            print("No user data found. Please run a Rootly analysis first.")
            return
        
        print("\n🔥 Creating Incidents Based on Stored Burnout Data")
        print("=" * 60)
        print("\nTeam Members and Their Burnout Risk:")
        
        # Categorize users by risk level
        high_risk = [u for u in users if u['risk_level'] == 'high']
        medium_risk = [u for u in users if u['risk_level'] == 'medium']
        low_risk = [u for u in users if u['risk_level'] == 'low']
        
        for user in users:
            score_pct = user['burnout_score'] * 10  # Convert 0-10 to percentage
            print(f"\n{user['name']}:")
            print(f"  Email: {user['email']}")
            print(f"  Burnout Score: {score_pct:.1f}%")
            print(f"  Risk Level: {user['risk_level'].upper()}")
            print(f"  Past Incidents: {user['incident_count']}")
            if 'after_hours_percentage' in user['metrics']:
                print(f"  After-hours work: {user['metrics']['after_hours_percentage']:.1f}%")
        
        print("\n" + "=" * 60)
        print("\nCreating incidents to match burnout patterns...")
        
        # Incident scenarios
        incident_templates = [
            # Critical incidents (more likely to go to high-risk users)
            {"title": "[CRITICAL] Production database down", "urgency": "high", "prefer_high_risk": True},
            {"title": "[CRITICAL] Payment processing failures", "urgency": "high", "prefer_high_risk": True},
            {"title": "[PROD] API gateway 503 errors spiking", "urgency": "high", "prefer_high_risk": True},
            {"title": "[ALERT] Security breach attempt detected", "urgency": "high", "prefer_high_risk": True},
            
            # After-hours incidents (simulate based on actual patterns)
            {"title": "[AFTER-HOURS] Server memory critical", "urgency": "high", "after_hours": True},
            {"title": "[NIGHT] Automated deployment failed", "urgency": "high", "after_hours": True},
            {"title": "[WEEKEND] Backup job failed", "urgency": "low", "weekend": True},
            
            # Normal incidents
            {"title": "[WARN] Disk usage above 80%", "urgency": "low", "prefer_high_risk": False},
            {"title": "[INFO] SSL certificate expiring in 30 days", "urgency": "low", "prefer_high_risk": False},
            {"title": "[PROD] Cache performance degraded", "urgency": "low", "prefer_high_risk": False},
            {"title": "[STAGING] Test suite failures", "urgency": "low", "prefer_high_risk": False},
        ]
        
        created_count = 0
        
        for template in incident_templates:
            # Determine assignment based on burnout patterns
            if template.get('prefer_high_risk') and high_risk:
                # High-risk users handle critical incidents (burnout pattern)
                assigned_user = random.choice(high_risk)
            elif template.get('after_hours') and high_risk:
                # High-risk users work after hours
                assigned_user = random.choice(high_risk)
            elif template.get('weekend') and (high_risk or medium_risk):
                # High/medium risk users work weekends
                candidates = high_risk + medium_risk
                assigned_user = random.choice(candidates) if candidates else random.choice(users)
            else:
                # Normal distribution with bias towards incident count
                # Users with more past incidents are more likely to get new ones
                weights = [u['incident_count'] + 1 for u in users]  # +1 to avoid zero weight
                assigned_user = random.choices(users, weights=weights)[0]
            
            # Create the incident
            print(f"\n📋 Creating: {template['title']}")
            print(f"   Assigned to: {assigned_user['name']} (Risk: {assigned_user['risk_level']})")
            
            description = (f"Test incident for burnout pattern simulation.\n"
                         f"Assigned to {assigned_user['name']} based on burnout risk analysis.\n"
                         f"User burnout score: {assigned_user['burnout_score']*10:.1f}%")
            
            incident = self.create_incident(
                title=template['title'],
                urgency=template['urgency'],
                description=description,
                assigned_to=assigned_user['name']
            )
            
            if incident:
                created_count += 1
                print(f"   ✓ Created incident {incident['id']}")
            
            time.sleep(1)  # Rate limiting
        
        print("\n" + "=" * 60)
        print(f"\n✅ Created {created_count} incidents based on stored burnout data")
        print("\n📊 Pattern Summary:")
        print(f"   - High-risk users ({len(high_risk)}): Assigned critical & after-hours incidents")
        print(f"   - Medium-risk users ({len(medium_risk)}): Normal distribution")
        print(f"   - Low-risk users ({len(low_risk)}): Fewer incidents")
        print("\n💡 These incidents will reinforce the burnout patterns when analyzed!")
        
        # Show distribution
        if created_count > 0:
            print("\n📈 Expected reinforcement of burnout patterns:")
            for user in high_risk[:3]:  # Show top 3 high-risk users
                print(f"   - {user['name']}: Burnout score likely to increase")


def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description="Create PagerDuty incidents using stored Rootly analysis data"
    )
    parser.add_argument(
        "--db-path", 
        default="../backend/app.db",
        help="Path to the SQLite database (default: ../backend/app.db)"
    )
    parser.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of incidents to create (default: 10)"
    )
    
    args = parser.parse_args()
    
    # Check if database exists
    if not os.path.exists(args.db_path):
        print(f"❌ Database not found at {args.db_path}")
        print("Please ensure you've run a Rootly analysis first")
        return
    
    creator = StoredDataIncidentCreator(PD_API_TOKEN, args.db_path)
    creator.simulate_realistic_burnout_pattern()


if __name__ == "__main__":
    main()