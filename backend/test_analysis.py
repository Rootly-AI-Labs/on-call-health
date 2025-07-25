#!/usr/bin/env python3
"""
Test script for analysis functionality.
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.core.simple_burnout_analyzer import SimpleBurnoutAnalyzer

client = TestClient(app)

def test_analysis_endpoints():
    """Test analysis endpoints."""
    print("📊 Testing Analysis Endpoints...")
    print("=" * 45)
    
    # Test analysis start without auth (should fail)
    response = client.post("/analysis/start", json={"days_back": 30})
    print(f"Start analysis without auth status: {response.status_code}")
    if response.status_code == 403:
        print("✅ Analysis start correctly requires authentication")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
    
    # Test analysis status without auth (should fail)
    response = client.get("/analysis/1")
    print(f"Analysis status without auth status: {response.status_code}")
    if response.status_code == 403:
        print("✅ Analysis status correctly requires authentication")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
    
    # Test current analysis without auth (should fail)
    response = client.get("/analysis/current")
    print(f"Current analysis without auth status: {response.status_code}")
    if response.status_code == 403:
        print("✅ Current analysis correctly requires authentication")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")
    
    # Test analysis history without auth (should fail)
    response = client.get("/analysis/history")
    print(f"Analysis history without auth status: {response.status_code}")
    if response.status_code == 403:
        print("✅ Analysis history correctly requires authentication")
    else:
        print(f"⚠️ Unexpected response: {response.status_code}")

def test_burnout_analyzer():
    """Test the burnout analyzer with mock data."""
    print("\n🧠 Testing Burnout Analyzer...")
    print("=" * 40)
    
    try:
        analyzer = SimpleBurnoutAnalyzer("test_token")
        print("✅ SimpleBurnoutAnalyzer imported and instantiated")
        
        # Create mock data
        mock_users = [
            {
                "id": "1",
                "attributes": {
                    "full_name": "John Doe",
                    "email": "john@example.com"
                }
            },
            {
                "id": "2", 
                "attributes": {
                    "full_name": "Jane Smith",
                    "email": "jane@example.com"
                }
            }
        ]
        
        mock_incidents = [
            {
                "id": "inc_1",
                "attributes": {
                    "created_at": "2024-01-01T15:30:00Z",
                    "started_at": "2024-01-01T15:30:00Z",
                    "resolved_at": "2024-01-01T17:30:00Z",
                    "user": {"data": {"id": "1"}},
                    "resolved_by": {"data": {"id": "1"}}
                }
            },
            {
                "id": "inc_2",
                "attributes": {
                    "created_at": "2024-01-02T22:00:00Z",  # After hours
                    "started_at": "2024-01-02T22:00:00Z",
                    "resolved_at": "2024-01-03T02:00:00Z",  # 4 hours later
                    "user": {"data": {"id": "1"}},
                    "resolved_by": {"data": {"id": "2"}}
                }
            }
        ]
        
        mock_metadata = {
            "days_analyzed": 30,
            "total_users": 2,
            "total_incidents": 2
        }
        
        # Run analysis
        results = analyzer.analyze_team_burnout(mock_users, mock_incidents, mock_metadata)
        
        print("✅ Analysis completed successfully")
        print(f"   Team summary: {results.get('team_summary', {})}")
        print(f"   Users analyzed: {len(results.get('team_analysis', []))}")
        
        # Check structure
        required_fields = ["analysis_timestamp", "metadata", "team_summary", "team_analysis", "recommendations"]
        for field in required_fields:
            if field in results:
                print(f"✅ Field '{field}' present in results")
            else:
                print(f"❌ Field '{field}' missing from results")
        
        # Check team analysis structure
        if results.get("team_analysis"):
            user_analysis = results["team_analysis"][0]
            user_fields = ["user_id", "user_name", "burnout_score", "risk_level", "key_metrics", "recommendations"]
            for field in user_fields:
                if field in user_analysis:
                    print(f"✅ User analysis field '{field}' present")
                else:
                    print(f"❌ User analysis field '{field}' missing")
        
        print("✅ Burnout analyzer test completed successfully")
        
    except Exception as e:
        print(f"❌ Burnout analyzer test failed: {e}")

if __name__ == "__main__":
    test_analysis_endpoints()
    test_burnout_analyzer()