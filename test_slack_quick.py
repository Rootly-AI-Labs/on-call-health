#!/usr/bin/env python3
"""Quick test to verify Slack scopes work with a simple API call"""

import requests
import json

# Test the Slack integration check endpoint
try:
    # This will test the current integration
    response = requests.get("http://localhost:8000/integrations/slack/status")
    if response.status_code == 200:
        data = response.json()
        print("✅ Slack Integration Status:")
        print(f"   Connected: {data.get('connected', False)}")
        if data.get('connected'):
            integration = data.get('integration', {})
            print(f"   Total Channels: {integration.get('total_channels', 0)}")
            print(f"   Token Preview: {integration.get('token_preview', 'N/A')}")
            print(f"   Webhook Preview: {integration.get('webhook_preview', 'N/A')}")
            print(f"   Channel Names: {integration.get('channel_names', [])}")
            
            # Check for errors
            if 'channels_error' in integration:
                print(f"   ❌ Channels Error: {integration['channels_error']}")
            else:
                print(f"   ✅ Channels: {len(integration.get('channel_names', []))} found")
        else:
            print("   ❌ Not connected")
    else:
        print(f"❌ API Error: {response.status_code}")
        print(f"   Response: {response.text}")
        
except Exception as e:
    print(f"❌ Exception: {e}")