#!/usr/bin/env python3
"""
Simulate a realistic burnout pattern in PagerDuty
Creates incidents and assigns them to create burnout risk patterns
"""

import requests
import json
import random
import time
from datetime import datetime, timedelta

PD_API_TOKEN = "u+yU3VeLnT_d1HuYzDrg"
PD_SERVICE_ID = "PB02TQZ"

class BurnoutSimulator:
    def __init__(self, pd_token: str):
        self.pd_token = pd_token
        self.headers = {
            "Authorization": f"Token token={pd_token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json"
        }
        
        # Define team members with burnout patterns
        self.team_patterns = {
            "Alex Chen": {
                "email": "alex@example.com",
                "pattern": "high_burnout",
                "incident_percentage": 40,  # Handles 40% of incidents
                "after_hours": True,
                "weekend_work": True,
                "response_time": "fast"  # Always responds quickly (sign of overwork)
            },
            "Sarah Johnson": {
                "email": "sarah@example.com", 
                "pattern": "high_burnout",
                "incident_percentage": 35,  # Handles 35% of incidents
                "after_hours": True,
                "weekend_work": True,
                "response_time": "fast"
            },
            "Mike Williams": {
                "email": "mike@example.com",
                "pattern": "medium_risk",
                "incident_percentage": 15,
                "after_hours": False,
                "weekend_work": False,
                "response_time": "normal"
            },
            "Emma Davis": {
                "email": "emma@example.com",
                "pattern": "low_risk",
                "incident_percentage": 10,
                "after_hours": False,
                "weekend_work": False,
                "response_time": "normal"
            }
        }
    
    def create_incident_with_assignment(self, title: str, urgency: str, assigned_to: str, 
                                      created_at_hour: int = None) -> Dict:
        """Create an incident and simulate assignment pattern"""
        
        # First create the incident
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
                    "details": f"Assigned to {assigned_to} - Burnout pattern simulation"
                }
            }
        }
        
        response = requests.post(
            "https://api.pagerduty.com/incidents",
            headers=self.headers,
            json=incident_data
        )
        
        if response.status_code == 201:
            incident = response.json()["incident"]
            
            # Add a note about who handled it (for tracking)
            note_data = {
                "note": {
                    "content": f"Incident handled by {assigned_to}"
                }
            }
            
            requests.post(
                f"https://api.pagerduty.com/incidents/{incident['id']}/notes",
                headers=self.headers,
                json=note_data
            )
            
            return incident
        else:
            print(f"Error creating incident: {response.status_code}")
            return None
    
    def simulate_burnout_scenario(self):
        """Create incidents that demonstrate burnout patterns"""
        
        print("🔥 Simulating Burnout Patterns in PagerDuty")
        print("=" * 60)
        print("\nTeam Burnout Profiles:")
        for name, pattern in self.team_patterns.items():
            print(f"\n{name}:")
            print(f"  - Handles {pattern['incident_percentage']}% of incidents")
            print(f"  - After-hours work: {pattern['after_hours']}")
            print(f"  - Weekend work: {pattern['weekend_work']}")
            print(f"  - Burnout risk: {pattern['pattern']}")
        
        print("\n" + "=" * 60)
        print("\nCreating incident patterns...")
        
        # Incident scenarios
        incidents = [
            # Regular hours incidents
            {"title": "[PROD] API latency spike detected", "urgency": "high", "hour": 10},
            {"title": "[PROD] Database connection timeout", "urgency": "high", "hour": 14},
            {"title": "[WARN] Memory usage above 80%", "urgency": "low", "hour": 11},
            {"title": "[PROD] Payment gateway errors", "urgency": "high", "hour": 15},
            {"title": "[WARN] Disk space warning", "urgency": "low", "hour": 13},
            
            # After-hours incidents (handled by high burnout team members)
            {"title": "[CRITICAL] Site down - 503 errors", "urgency": "high", "hour": 23},
            {"title": "[PROD] Database replication failure", "urgency": "high", "hour": 2},
            {"title": "[ALERT] Spike in failed login attempts", "urgency": "high", "hour": 3},
            {"title": "[PROD] Cache server unresponsive", "urgency": "high", "hour": 22},
            
            # Weekend incidents (also handled by high burnout members)
            {"title": "[WEEKEND] Backup job failed", "urgency": "low", "hour": 9, "weekend": True},
            {"title": "[WEEKEND] SSL cert expiring", "urgency": "high", "hour": 14, "weekend": True},
            {"title": "[WEEKEND] Automated deployment failed", "urgency": "high", "hour": 16, "weekend": True},
        ]
        
        created_count = 0
        
        for incident_data in incidents:
            # Determine who handles this incident based on patterns
            hour = incident_data.get("hour", 12)
            is_weekend = incident_data.get("weekend", False)
            is_after_hours = hour < 9 or hour > 17
            
            # Assign based on burnout pattern
            if is_after_hours or is_weekend:
                # High burnout members handle after-hours/weekend
                eligible = [name for name, p in self.team_patterns.items() 
                          if p["after_hours"] or (is_weekend and p["weekend_work"])]
                assigned_to = random.choice(eligible) if eligible else "Alex Chen"
            else:
                # Weighted random assignment during normal hours
                weights = [p["incident_percentage"] for p in self.team_patterns.values()]
                assigned_to = random.choices(list(self.team_patterns.keys()), weights=weights)[0]
            
            # Create the incident
            time_str = "weekend" if is_weekend else f"{hour}:00"
            print(f"\n📋 Creating: {incident_data['title']}")
            print(f"   Time: {time_str}, Assigned to: {assigned_to}")
            
            incident = self.create_incident_with_assignment(
                title=incident_data["title"],
                urgency=incident_data["urgency"],
                assigned_to=assigned_to,
                created_at_hour=hour
            )
            
            if incident:
                created_count += 1
                print(f"   ✓ Created incident {incident['id']}")
                
                # Simulate response time based on team member pattern
                response_pattern = self.team_patterns[assigned_to]["response_time"]
                if response_pattern == "fast":
                    print(f"   ⚡ {assigned_to} responds immediately (burnout indicator)")
                else:
                    print(f"   ⏱️  {assigned_to} responds normally")
            
            time.sleep(1)  # Rate limiting
        
        print("\n" + "=" * 60)
        print(f"\n✅ Created {created_count} incidents with burnout patterns")
        print("\n🎯 Expected Burnout Analysis Results:")
        print("   - Alex Chen & Sarah Johnson: HIGH RISK (75%+ of incidents, after-hours)")
        print("   - Mike Williams: MEDIUM RISK (normal hours only)")
        print("   - Emma Davis: LOW RISK (few incidents, normal hours)")
        print("\n💡 Run your Rootly burnout analysis to see these patterns detected!")


def main():
    simulator = BurnoutSimulator(PD_API_TOKEN)
    simulator.simulate_burnout_scenario()


if __name__ == "__main__":
    main()