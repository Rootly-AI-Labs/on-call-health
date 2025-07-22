#!/usr/bin/env python3
"""Test script to verify mock Slack data collection works with original detector's data."""

import asyncio
import sys
import os
sys.path.append('backend')

from app.services.slack_collector import SlackCollector, collect_team_slack_data

async def test_mock_slack_collection():
    print("Testing mock Slack data collection...")
    
    # Test users from original detector config
    test_emails = [
        "sylvain@rootly.com",
        "spencer.cheng@rootly.com", 
        "jasmeet.singh@rootly.com"
    ]
    
    print(f"Testing with emails: {test_emails}")
    
    # Test with mock mode (should read from original detector files)
    print("\n=== Testing Mock Mode (from original detector files) ===")
    slack_data = await collect_team_slack_data(test_emails, days=30, mock_mode=True)
    
    print(f"Collected data for {len(slack_data)} users:")
    for email, data in slack_data.items():
        if data:
            metrics = data['metrics']
            print(f"\n{email}:")
            print(f"  User ID: {data['user_id']}")
            print(f"  Total messages: {metrics['total_messages']}")
            print(f"  Messages/day: {metrics['messages_per_day']}")
            print(f"  After hours: {metrics['after_hours_percentage']*100:.1f}%")
            print(f"  Weekend: {metrics['weekend_percentage']*100:.1f}%")
            print(f"  Channels: {metrics['channel_diversity']}")
            print(f"  DM ratio: {metrics['dm_ratio']*100:.1f}%")
        else:
            print(f"\n{email}: No data found")
    
    # Test with regular mode (should use generated mock data)
    print("\n=== Testing Regular Mode (generated mock data) ===")
    slack_data_regular = await collect_team_slack_data(test_emails, days=30, mock_mode=False)
    
    print(f"Collected data for {len(slack_data_regular)} users:")
    for email, data in slack_data_regular.items():
        if data:
            metrics = data['metrics']
            print(f"\n{email}:")
            print(f"  User ID: {data['user_id']}")
            print(f"  Total messages: {metrics['total_messages']}")
            print(f"  Messages/day: {metrics['messages_per_day']}")
            print(f"  After hours: {metrics['after_hours_percentage']*100:.1f}%")
            print(f"  Weekend: {metrics['weekend_percentage']*100:.1f}%")
            print(f"  Channels: {metrics['channel_diversity']}")
        else:
            print(f"\n{email}: No data found")

if __name__ == "__main__":
    asyncio.run(test_mock_slack_collection())