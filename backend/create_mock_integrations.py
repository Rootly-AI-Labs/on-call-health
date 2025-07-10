#!/usr/bin/env python3
"""
Create mock GitHub and Slack integrations for testing.
"""

import sys
import os
sys.path.append('.')

from app.models import get_db, GitHubIntegration, SlackIntegration, User
from sqlalchemy.orm import Session

def create_mock_integrations():
    """Create mock GitHub and Slack integrations for existing users."""
    db = next(get_db())
    
    try:
        # Get some users from the database
        users = db.query(User).limit(10).all()
        print(f"Found {len(users)} users in database")
        
        if not users:
            print("No users found in database!")
            return
        
        # Sample GitHub usernames (these would be real in production)
        github_usernames = [
            "spencerhcheng", "jasmeetluthra", "sylvainkalache", "christomitov", 
            "ibrahimelchami", "weihanli101", "alexmingoia", "kwent", 
            "gid-rootly", "dansadler1"
        ]
        
        # Sample Slack user IDs (these would be real in production)
        slack_user_ids = [
            "U001SPENCER", "U002JASMEET", "U003SYLVAIN", "U004CHRISTO",
            "U005IBRAHIM", "U006WEIHAN", "U007ALEX", "U008QUENTIN", 
            "U009GIDEON", "U010DAN"
        ]
        
        github_integrations_created = 0
        slack_integrations_created = 0
        
        for i, user in enumerate(users):
            if i < len(github_usernames):
                # Check if GitHub integration already exists
                existing_github = db.query(GitHubIntegration).filter(
                    GitHubIntegration.user_id == user.id
                ).first()
                
                if not existing_github:
                    github_integration = GitHubIntegration(
                        user_id=user.id,
                        github_username=github_usernames[i],
                        organizations=["rootlyhq", "Rootly-AI-Labs"],
                        token_source="oauth",
                        connected_at=user.created_at,
                        last_updated=user.created_at
                    )
                    db.add(github_integration)
                    github_integrations_created += 1
                    print(f"Created GitHub integration for {user.email} -> {github_usernames[i]}")
            
            if i < len(slack_user_ids):
                # Check if Slack integration already exists
                existing_slack = db.query(SlackIntegration).filter(
                    SlackIntegration.user_id == user.id
                ).first()
                
                if not existing_slack:
                    slack_integration = SlackIntegration(
                        user_id=user.id,
                        slack_user_id=slack_user_ids[i],
                        workspace_id="T0001ROOTLY",
                        token_source="oauth",
                        connected_at=user.created_at,
                        last_updated=user.created_at,
                        total_channels=15
                    )
                    db.add(slack_integration)
                    slack_integrations_created += 1
                    print(f"Created Slack integration for {user.email} -> {slack_user_ids[i]}")
        
        db.commit()
        print(f"\n✅ Created {github_integrations_created} GitHub integrations")
        print(f"✅ Created {slack_integrations_created} Slack integrations")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_mock_integrations()