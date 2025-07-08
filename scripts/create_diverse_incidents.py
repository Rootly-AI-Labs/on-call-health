#!/usr/bin/env python3
"""
Create diverse incidents with various team members
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

# Diverse team with various backgrounds
team_members = [
    "David Kim",
    "Maria Garcia", 
    "John Thompson",
    "Priya Patel",
    "James Wilson",
    "Lisa Zhang",
    "Carlos Rodriguez",
    "Anna Kowalski",
    "Mohammed Ali",
    "Rachel Green",
    "Tom Anderson",
    "Nina Volkov",
    "Robert Taylor",
    "Yuki Tanaka",
    "Elena Dimitrov"
]

# Diverse incident scenarios
incident_scenarios = [
    # Infrastructure issues
    {"title": "Kubernetes pod crash loop in production cluster", "urgency": "high", "category": "infrastructure"},
    {"title": "Redis cache cluster split-brain detected", "urgency": "high", "category": "infrastructure"},
    {"title": "ElasticSearch index corruption on node-03", "urgency": "high", "category": "infrastructure"},
    {"title": "Docker registry storage full - builds failing", "urgency": "high", "category": "infrastructure"},
    {"title": "Load balancer health checks failing intermittently", "urgency": "low", "category": "infrastructure"},
    
    # Security incidents
    {"title": "Suspicious login attempts from unknown IP range", "urgency": "high", "category": "security"},
    {"title": "WAF blocking legitimate traffic - false positives", "urgency": "low", "category": "security"},
    {"title": "SSH brute force attempts detected on bastion host", "urgency": "high", "category": "security"},
    {"title": "Expired SSL certificate on api.staging.domain", "urgency": "low", "category": "security"},
    {"title": "DDoS attack detected - rate limiting activated", "urgency": "high", "category": "security"},
    
    # Application errors
    {"title": "NullPointerException in payment processing service", "urgency": "high", "category": "application"},
    {"title": "Memory leak in user authentication service", "urgency": "high", "category": "application"},
    {"title": "GraphQL query timeout on complex nested queries", "urgency": "low", "category": "application"},
    {"title": "Race condition in order fulfillment workflow", "urgency": "high", "category": "application"},
    {"title": "Deprecated API endpoint still receiving traffic", "urgency": "low", "category": "application"},
    
    # Database issues
    {"title": "PostgreSQL replication lag exceeding 10 minutes", "urgency": "high", "category": "database"},
    {"title": "MongoDB connection pool exhausted", "urgency": "high", "category": "database"},
    {"title": "Slow query blocking table - customer_orders", "urgency": "high", "category": "database"},
    {"title": "Database backup job failed - insufficient space", "urgency": "low", "category": "database"},
    {"title": "Deadlock detected in transaction processing", "urgency": "high", "category": "database"},
    
    # Network and CDN
    {"title": "CDN origin timeout - assets not loading", "urgency": "high", "category": "network"},
    {"title": "Cross-region latency spike detected", "urgency": "low", "category": "network"},
    {"title": "BGP route flapping on primary ISP", "urgency": "high", "category": "network"},
    {"title": "Packet loss detected on internal network", "urgency": "low", "category": "network"},
    {"title": "DNS resolution failures for third-party service", "urgency": "high", "category": "network"},
    
    # Monitoring and observability
    {"title": "Prometheus scraping failures - metrics missing", "urgency": "low", "category": "monitoring"},
    {"title": "Log aggregation pipeline backlog growing", "urgency": "low", "category": "monitoring"},
    {"title": "APM agent causing performance degradation", "urgency": "high", "category": "monitoring"},
    {"title": "Alert fatigue - too many false alarms", "urgency": "low", "category": "monitoring"},
    {"title": "Distributed tracing spans not correlating", "urgency": "low", "category": "monitoring"},
    
    # Third-party integrations
    {"title": "Stripe webhook failures - payments not updating", "urgency": "high", "category": "integration"},
    {"title": "SendGrid API rate limit exceeded", "urgency": "low", "category": "integration"},
    {"title": "Salesforce sync job failing with auth errors", "urgency": "low", "category": "integration"},
    {"title": "Twillio SMS delivery delays reported", "urgency": "low", "category": "integration"},
    {"title": "Google Maps API quota exceeded", "urgency": "low", "category": "integration"},
    
    # Performance issues
    {"title": "Homepage load time exceeding 5 seconds", "urgency": "high", "category": "performance"},
    {"title": "Search indexing lagging by 2 hours", "urgency": "low", "category": "performance"},
    {"title": "Report generation timing out for large datasets", "urgency": "low", "category": "performance"},
    {"title": "API response time p99 above SLA", "urgency": "high", "category": "performance"},
    {"title": "Background job queue processing slowed", "urgency": "low", "category": "performance"},
]

def create_incident(title, urgency, handler):
    """Create an incident with detailed context"""
    
    body = {
        "incident": {
            "type": "incident",
            "title": f"{title} - Handled by {handler}",
            "service": {
                "id": PD_SERVICE_ID,
                "type": "service_reference"
            },
            "urgency": urgency,
            "body": {
                "type": "incident_body",
                "details": f"Incident detected and handled by {handler}.\nThis is a simulated incident for testing burnout detection across diverse scenarios."
            }
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
        print(f"Error: {response.status_code} - {response.text[:100]}")
        return None

print("🌈 Creating Diverse Incidents with Various Team Members")
print("=" * 70)
print(f"\nTeam members involved: {len(team_members)}")
print(f"Incident scenarios: {len(incident_scenarios)}")
print("\n" + "=" * 70)

created_count = 0
failed_count = 0

# Shuffle scenarios for variety
random.shuffle(incident_scenarios)

# Create incidents
for i, scenario in enumerate(incident_scenarios):
    # Randomly assign to team member
    handler = random.choice(team_members)
    
    print(f"\n[{i+1}/{len(incident_scenarios)}] Creating incident...")
    print(f"  📋 {scenario['title'][:50]}...")
    print(f"  👤 Handler: {handler}")
    print(f"  🚨 Urgency: {scenario['urgency']}")
    print(f"  📁 Category: {scenario['category']}")
    
    incident = create_incident(
        title=scenario['title'],
        urgency=scenario['urgency'],
        handler=handler
    )
    
    if incident:
        created_count += 1
        print(f"  ✅ Success! Incident ID: {incident['id']}")
        
        # Add a note with more context
        note_body = {
            "note": {
                "content": (f"Incident Details:\n"
                          f"- Handled by: {handler}\n"
                          f"- Category: {scenario['category']}\n"
                          f"- Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                          f"- Simulated for burnout detection testing")
            }
        }
        
        requests.post(
            f"https://api.pagerduty.com/incidents/{incident['id']}/notes",
            headers=headers,
            json=note_body
        )
    else:
        failed_count += 1
        print(f"  ❌ Failed to create incident")
    
    # Rate limiting
    time.sleep(1.5)
    
    # Optional: Stop after 20 to avoid too many
    if created_count >= 20:
        print("\n⚠️  Reached 20 incidents, stopping to avoid overload...")
        break

print("\n" + "=" * 70)
print(f"\n📊 Summary:")
print(f"  ✅ Successfully created: {created_count} incidents")
if failed_count > 0:
    print(f"  ❌ Failed: {failed_count} incidents")

print(f"\n👥 Random distribution across {len(team_members)} team members:")
print("  - David Kim, Maria Garcia, John Thompson, Priya Patel...")
print("  - And 11 more team members")

print("\n📈 Incident categories created:")
categories = set(s['category'] for s in incident_scenarios[:created_count])
for cat in categories:
    count = sum(1 for s in incident_scenarios[:created_count] if s['category'] == cat)
    print(f"  - {cat.capitalize()}: {count} incidents")

print("\n💡 These diverse incidents will provide rich data for burnout analysis!")
print("   The random distribution should show a more realistic operational pattern.")