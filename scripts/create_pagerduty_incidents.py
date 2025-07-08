#!/usr/bin/env python3
"""
Script to create test incidents in PagerDuty
"""

import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
import argparse
import random

class PagerDutyIncidentCreator:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://api.pagerduty.com"
        self.headers = {
            "Authorization": f"Token token={api_token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json"
        }
    
    def get_services(self) -> List[Dict]:
        """Get list of available services"""
        response = requests.get(
            f"{self.base_url}/services",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["services"]
    
    def get_users(self) -> List[Dict]:
        """Get list of users"""
        response = requests.get(
            f"{self.base_url}/users",
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()["users"]
    
    def create_incident(
        self,
        title: str,
        service_id: str,
        urgency: str = "high",
        description: Optional[str] = None,
        incident_key: Optional[str] = None,
        assignee_id: Optional[str] = None
    ) -> Dict:
        """Create a single incident"""
        
        incident_data = {
            "incident": {
                "type": "incident",
                "title": title,
                "service": {
                    "id": service_id,
                    "type": "service_reference"
                },
                "urgency": urgency,
                "body": {
                    "type": "incident_body",
                    "details": description or f"Test incident created at {datetime.now()}"
                }
            }
        }
        
        if incident_key:
            incident_data["incident"]["incident_key"] = incident_key
            
        if assignee_id:
            incident_data["incident"]["assignments"] = [{
                "assignee": {
                    "id": assignee_id,
                    "type": "user_reference"
                }
            }]
        
        response = requests.post(
            f"{self.base_url}/incidents",
            headers=self.headers,
            json=incident_data
        )
        response.raise_for_status()
        return response.json()["incident"]
    
    def create_test_incidents(
        self,
        service_id: str,
        count: int = 5,
        urgency_mix: Dict[str, float] = None,
        assign_to_users: Optional[List[str]] = None
    ) -> List[Dict]:
        """Create multiple test incidents with various characteristics"""
        
        if urgency_mix is None:
            urgency_mix = {"high": 0.3, "low": 0.7}
        
        incident_titles = [
            "Database connection timeout",
            "High CPU usage detected",
            "API response time degradation",
            "Memory leak in production",
            "Disk space running low",
            "SSL certificate expiring soon",
            "Failed authentication attempts spike",
            "Queue backlog increasing",
            "Service health check failing",
            "Network latency spike detected",
            "Cache hit rate dropping",
            "Error rate above threshold",
            "Deployment rollback required",
            "Data sync lag detected",
            "Load balancer unhealthy instances"
        ]
        
        incident_descriptions = [
            "Automated monitoring detected an issue requiring investigation",
            "Performance degradation observed in production environment",
            "Critical threshold exceeded for monitored metric",
            "System anomaly detected by automated checks",
            "Infrastructure component showing signs of instability"
        ]
        
        created_incidents = []
        
        for i in range(count):
            # Determine urgency based on mix
            rand = random.random()
            urgency = "high" if rand < urgency_mix.get("high", 0.3) else "low"
            
            # Select random title and description
            title = random.choice(incident_titles)
            description = random.choice(incident_descriptions)
            
            # Select assignee if provided
            assignee_id = None
            if assign_to_users:
                assignee_id = random.choice(assign_to_users)
            
            try:
                print(f"Creating incident {i+1}/{count}: {title} (urgency: {urgency})")
                incident = self.create_incident(
                    title=f"[TEST] {title}",
                    service_id=service_id,
                    urgency=urgency,
                    description=f"[TEST INCIDENT] {description}",
                    incident_key=f"test-{int(time.time())}-{i}",
                    assignee_id=assignee_id
                )
                created_incidents.append(incident)
                print(f"  ✓ Created: {incident['id']} - {incident['title']}")
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ✗ Failed to create incident: {e}")
        
        return created_incidents
    
    def resolve_incident(self, incident_id: str, resolution_notes: str = "Resolved by automation") -> Dict:
        """Resolve an incident"""
        
        update_data = {
            "incident": {
                "type": "incident",
                "status": "resolved",
                "resolution": resolution_notes
            }
        }
        
        response = requests.put(
            f"{self.base_url}/incidents/{incident_id}",
            headers=self.headers,
            json=update_data
        )
        response.raise_for_status()
        return response.json()["incident"]
    
    def list_recent_incidents(self, limit: int = 10) -> List[Dict]:
        """List recent incidents"""
        response = requests.get(
            f"{self.base_url}/incidents",
            headers=self.headers,
            params={"limit": limit, "sort_by": "created_at:desc"}
        )
        response.raise_for_status()
        return response.json()["incidents"]


def main():
    parser = argparse.ArgumentParser(description="Create test incidents in PagerDuty")
    parser.add_argument("--token", required=True, help="PagerDuty API token")
    parser.add_argument("--service-id", help="Service ID to create incidents for")
    parser.add_argument("--count", type=int, default=5, help="Number of incidents to create (default: 5)")
    parser.add_argument("--list-services", action="store_true", help="List available services")
    parser.add_argument("--list-users", action="store_true", help="List available users")
    parser.add_argument("--assign-randomly", action="store_true", help="Randomly assign incidents to users")
    parser.add_argument("--urgency-high-pct", type=float, default=30, help="Percentage of high urgency incidents (default: 30)")
    parser.add_argument("--auto-resolve", type=int, help="Auto-resolve incidents after N seconds")
    
    args = parser.parse_args()
    
    creator = PagerDutyIncidentCreator(args.token)
    
    # List services if requested
    if args.list_services:
        print("\nAvailable Services:")
        print("-" * 50)
        services = creator.get_services()
        for service in services:
            print(f"ID: {service['id']}")
            print(f"Name: {service['name']}")
            print(f"Status: {service['status']}")
            print("-" * 50)
        return
    
    # List users if requested
    if args.list_users:
        print("\nAvailable Users:")
        print("-" * 50)
        users = creator.get_users()
        for user in users:
            print(f"ID: {user['id']}")
            print(f"Name: {user['name']}")
            print(f"Email: {user['email']}")
            print("-" * 50)
        return
    
    # Create incidents
    if not args.service_id:
        print("Error: --service-id is required to create incidents")
        print("Use --list-services to see available services")
        return
    
    # Get users for assignment if requested
    assign_to_users = None
    if args.assign_randomly:
        users = creator.get_users()
        assign_to_users = [user['id'] for user in users]
        print(f"Will randomly assign to {len(assign_to_users)} users")
    
    # Calculate urgency mix
    urgency_mix = {
        "high": args.urgency_high_pct / 100,
        "low": 1 - (args.urgency_high_pct / 100)
    }
    
    print(f"\nCreating {args.count} test incidents...")
    print(f"Service ID: {args.service_id}")
    print(f"Urgency mix: {args.urgency_high_pct}% high, {100-args.urgency_high_pct}% low")
    print("-" * 50)
    
    incidents = creator.create_test_incidents(
        service_id=args.service_id,
        count=args.count,
        urgency_mix=urgency_mix,
        assign_to_users=assign_to_users
    )
    
    print(f"\nSuccessfully created {len(incidents)} incidents")
    
    # Auto-resolve if requested
    if args.auto_resolve:
        print(f"\nWaiting {args.auto_resolve} seconds before resolving...")
        time.sleep(args.auto_resolve)
        
        print("Resolving incidents...")
        for incident in incidents:
            try:
                creator.resolve_incident(
                    incident['id'],
                    f"Auto-resolved after {args.auto_resolve} seconds (test incident)"
                )
                print(f"  ✓ Resolved: {incident['id']}")
            except Exception as e:
                print(f"  ✗ Failed to resolve {incident['id']}: {e}")
    
    # Show recent incidents
    print("\nRecent incidents:")
    print("-" * 50)
    recent = creator.list_recent_incidents(limit=10)
    for incident in recent:
        print(f"{incident['created_at']} - {incident['title']} ({incident['status']})")


if __name__ == "__main__":
    main()