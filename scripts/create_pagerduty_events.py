#!/usr/bin/env python3
"""
Create test incidents in PagerDuty using the Events API v2
This is simpler and requires only an integration key (routing key)
"""

import requests
import json
import time
import random
from datetime import datetime
from typing import List, Dict

def create_event(routing_key: str, summary: str, source: str = "test-script", 
                severity: str = "error", dedup_key: str = None) -> Dict:
    """
    Create a PagerDuty event (which becomes an incident)
    
    Args:
        routing_key: Integration key from PagerDuty service
        summary: Brief description of the event
        source: Source system name
        severity: critical, error, warning, or info
        dedup_key: Optional deduplication key
    """
    
    event_data = {
        "routing_key": routing_key,
        "event_action": "trigger",
        "payload": {
            "summary": summary,
            "source": source,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "custom_details": {
                "created_by": "test script",
                "environment": "test",
                "test_data": True
            }
        }
    }
    
    if dedup_key:
        event_data["dedup_key"] = dedup_key
    
    response = requests.post(
        "https://events.pagerduty.com/v2/enqueue",
        json=event_data
    )
    response.raise_for_status()
    return response.json()


def resolve_event(routing_key: str, dedup_key: str) -> Dict:
    """Resolve an existing event/incident"""
    
    event_data = {
        "routing_key": routing_key,
        "event_action": "resolve",
        "dedup_key": dedup_key
    }
    
    response = requests.post(
        "https://events.pagerduty.com/v2/enqueue",
        json=event_data
    )
    response.raise_for_status()
    return response.json()


def create_test_incidents(routing_key: str, count: int = 5) -> List[str]:
    """Create multiple test incidents with realistic data"""
    
    # Sample incident scenarios
    scenarios = [
        {
            "summary": "High CPU usage on production server prod-api-01",
            "severity": "critical",
            "source": "monitoring-system"
        },
        {
            "summary": "Database connection pool exhausted",
            "severity": "error",
            "source": "db-monitor"
        },
        {
            "summary": "API response time exceeding SLA threshold",
            "severity": "error",
            "source": "api-monitor"
        },
        {
            "summary": "Disk usage at 85% on data-server-03",
            "severity": "warning",
            "source": "infrastructure-monitor"
        },
        {
            "summary": "Memory leak detected in payment service",
            "severity": "critical",
            "source": "app-monitor"
        },
        {
            "summary": "Failed health checks on load balancer",
            "severity": "error",
            "source": "health-monitor"
        },
        {
            "summary": "Spike in 500 errors on checkout endpoint",
            "severity": "critical",
            "source": "error-tracking"
        },
        {
            "summary": "Background job queue backlog growing",
            "severity": "warning",
            "source": "queue-monitor"
        },
        {
            "summary": "SSL certificate expiring in 7 days",
            "severity": "warning",
            "source": "cert-monitor"
        },
        {
            "summary": "Unusual login activity detected",
            "severity": "error",
            "source": "security-monitor"
        }
    ]
    
    created_dedup_keys = []
    
    print(f"Creating {count} test incidents...")
    print("-" * 60)
    
    for i in range(count):
        scenario = random.choice(scenarios)
        dedup_key = f"test-incident-{int(time.time())}-{i}"
        
        try:
            summary = f"[TEST] {scenario['summary']}"
            print(f"Creating incident {i+1}/{count}:")
            print(f"  Summary: {summary}")
            print(f"  Severity: {scenario['severity']}")
            
            result = create_event(
                routing_key=routing_key,
                summary=summary,
                source=scenario['source'],
                severity=scenario['severity'],
                dedup_key=dedup_key
            )
            
            created_dedup_keys.append(dedup_key)
            print(f"  ✓ Created successfully (dedup_key: {dedup_key})")
            print(f"  Response: {result}")
            
            # Small delay to spread out incidents
            if i < count - 1:
                time.sleep(1)
                
        except Exception as e:
            print(f"  ✗ Failed to create incident: {e}")
    
    print("-" * 60)
    return created_dedup_keys


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Create test incidents in PagerDuty using Events API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create 5 test incidents
  python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY
  
  # Create 10 incidents and auto-resolve after 30 seconds
  python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY --count 10 --auto-resolve 30
  
  # Create a single custom incident
  python create_pagerduty_events.py --key YOUR_INTEGRATION_KEY --custom "Database backup failed"

To get your integration key:
1. Go to PagerDuty → Services → Your Service
2. Go to Integrations tab
3. Add an integration → Events API V2
4. Copy the Integration Key (Routing Key)
        """
    )
    
    parser.add_argument("--key", "-k", required=True, help="PagerDuty integration key (routing key)")
    parser.add_argument("--count", "-c", type=int, default=5, help="Number of incidents to create (default: 5)")
    parser.add_argument("--custom", help="Create a single incident with custom summary")
    parser.add_argument("--severity", choices=["critical", "error", "warning", "info"], 
                       default="error", help="Severity for custom incident")
    parser.add_argument("--auto-resolve", type=int, 
                       help="Auto-resolve incidents after N seconds")
    
    args = parser.parse_args()
    
    if args.custom:
        # Create a single custom incident
        print(f"Creating custom incident: {args.custom}")
        dedup_key = f"custom-{int(time.time())}"
        
        try:
            result = create_event(
                routing_key=args.key,
                summary=f"[TEST] {args.custom}",
                source="manual-test",
                severity=args.severity,
                dedup_key=dedup_key
            )
            print(f"✓ Created successfully")
            print(f"  Dedup key: {dedup_key}")
            print(f"  Response: {result}")
            
            if args.auto_resolve:
                print(f"\nWaiting {args.auto_resolve} seconds before resolving...")
                time.sleep(args.auto_resolve)
                resolve_result = resolve_event(args.key, dedup_key)
                print(f"✓ Resolved successfully")
                print(f"  Response: {resolve_result}")
                
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    else:
        # Create multiple test incidents
        dedup_keys = create_test_incidents(args.key, args.count)
        
        if args.auto_resolve and dedup_keys:
            print(f"\nWaiting {args.auto_resolve} seconds before resolving incidents...")
            time.sleep(args.auto_resolve)
            
            print("Resolving incidents...")
            print("-" * 60)
            
            for i, dedup_key in enumerate(dedup_keys):
                try:
                    result = resolve_event(args.key, dedup_key)
                    print(f"✓ Resolved incident {i+1}/{len(dedup_keys)} (dedup_key: {dedup_key})")
                except Exception as e:
                    print(f"✗ Failed to resolve incident {dedup_key}: {e}")


if __name__ == "__main__":
    main()