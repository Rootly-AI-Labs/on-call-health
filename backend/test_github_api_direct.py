#!/usr/bin/env python3
"""
Direct test of GitHub API to check for real data vs fake/mock data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.models.base import SessionLocal
from sqlalchemy import text
import json
import asyncio
from datetime import datetime, timedelta

async def test_github_api_direct():
    print("🔍 Testing GitHub API directly for real vs mock data...\n")
    
    try:
        # Get GitHub integration details
        with SessionLocal() as db:
            result = db.execute(text("""
                SELECT github_token, github_username, organizations, user_id 
                FROM github_integrations 
                LIMIT 1
            """)).fetchone()
            
            if not result:
                print("❌ No GitHub integration found")
                return
            
            github_token = result[0]
            github_username = result[1] 
            organizations = result[2]
            user_id = result[3]
            
            print(f"📊 Found GitHub integration:")
            print(f"  Username: {github_username}")
            print(f"  User ID: {user_id}")
            print(f"  Organizations: {organizations}")
            print(f"  Token: {'***' + github_token[-4:] if github_token else 'None'}\n")
        
        # Test GitHub API calls
        from app.services.github_collector import GitHubCollector
        
        collector = GitHubCollector()
        print("✅ GitHubCollector initialized\n")
        
        # Get team members from a recent analysis to test with
        with SessionLocal() as db:
            recent_analysis = db.execute(text("""
                SELECT results FROM analyses 
                WHERE status = 'completed' 
                ORDER BY created_at DESC 
                LIMIT 1
            """)).fetchone()
            
            if recent_analysis:
                results = json.loads(recent_analysis[0])
                team_members = results.get('team_analysis', {}).get('members', [])
                
                if team_members:
                    test_emails = [member.get('user_email') for member in team_members[:2]]  # Test with first 2
                    test_names = [member.get('user_name') for member in team_members[:2]]
                    
                    print(f"📧 Testing with emails: {test_emails}")
                    print(f"👥 Testing with names: {test_names}\n")
                    
                    # Test date range (last 7 days)
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    
                    print(f"📅 Date range: {start_date.date()} to {end_date.date()}\n")
                    
                    # Test the actual GitHub data collection
                    print("🔄 Attempting GitHub data collection...")
                    
                    try:
                        from app.services.github_collector import collect_team_github_data
                        from app.api.endpoints.github import decrypt_token
                        
                        # Decrypt the GitHub token
                        print("🔓 Decrypting GitHub token...")
                        try:
                            decrypted_token = decrypt_token(github_token)
                            print(f"✅ Token decrypted successfully")
                        except Exception as decrypt_error:
                            print(f"❌ Failed to decrypt token: {decrypt_error}")
                            decrypted_token = None
                        
                        # Calculate days for the range
                        days = (end_date - start_date).days
                        
                        github_data = await collect_team_github_data(
                            team_emails=test_emails,
                            days=days,
                            github_token=decrypted_token  # Use the decrypted token
                        )
                        
                        print("✅ GitHub API call successful!")
                        print(f"📊 Returned data structure:")
                        print(f"  Type: {type(github_data)}")
                        
                        if isinstance(github_data, dict):
                            print(f"  Keys: {list(github_data.keys())}")
                            
                            # Check each member's data
                            for email, member_data in github_data.items():
                                print(f"\n  👤 {email}:")
                                if isinstance(member_data, dict):
                                    print(f"    Data keys: {list(member_data.keys())}")
                                    
                                    # Check key metrics
                                    commits = member_data.get('commits_count', 0)
                                    prs = member_data.get('pull_requests_count', 0)
                                    reviews = member_data.get('reviews_count', 0)
                                    after_hours = member_data.get('after_hours_commits', 0)
                                    weekend = member_data.get('weekend_commits', 0)
                                    
                                    print(f"    Commits: {commits}")
                                    print(f"    Pull Requests: {prs}")
                                    print(f"    Reviews: {reviews}")
                                    print(f"    After Hours Commits: {after_hours}")
                                    print(f"    Weekend Commits: {weekend}")
                                    
                                    # Check the deeper structure for real vs mock indicators
                                    print(f"\n    🔍 DETAILED ANALYSIS:")
                                    
                                    # Check username correlation
                                    username = member_data.get('username')
                                    if username:
                                        print(f"    GitHub Username: {username}")
                                        if username == 'spencerhcheng':
                                            print(f"    ✅ REAL USERNAME MATCH - this is real data!")
                                    
                                    # Check activity_data for real API responses
                                    if 'activity_data' in member_data:
                                        activity = member_data['activity_data']
                                        print(f"    Activity data keys: {list(activity.keys()) if isinstance(activity, dict) else 'Not a dict'}")
                                        
                                        if isinstance(activity, dict):
                                            # Look for real GitHub API response patterns
                                            if 'commits' in activity:
                                                commits_data = activity['commits']
                                                print(f"    Commits data type: {type(commits_data)}")
                                                if isinstance(commits_data, list):
                                                    print(f"    Commits count: {len(commits_data)}")
                                                    if len(commits_data) > 0:
                                                        first_commit = commits_data[0]
                                                        print(f"    First commit keys: {list(first_commit.keys()) if isinstance(first_commit, dict) else 'Not a dict'}")
                                                        if 'sha' in str(first_commit):
                                                            print(f"    ✅ REAL COMMIT DATA - has SHA!")
                                            
                                            if 'pull_requests' in activity:
                                                prs_data = activity['pull_requests']
                                                print(f"    PRs data type: {type(prs_data)}")
                                                if isinstance(prs_data, list):
                                                    print(f"    PRs count: {len(prs_data)}")
                                            
                                            if 'organizations_searched' in activity:
                                                orgs = activity['organizations_searched']
                                                print(f"    Organizations searched: {orgs}")
                                                if 'rootlyhq' in str(orgs) or 'Rootly-AI-Labs' in str(orgs):
                                                    print(f"    ✅ SEARCHING REAL ORGS - this is definitely real data!")
                                    
                                    # Check for indicators this is real vs mock data
                                    if commits > 0 or prs > 0 or reviews > 0:
                                        print(f"    ✅ HAS ACTIVITY DATA - likely real!")
                                        
                                        # Look for specific patterns that indicate mock data
                                        if commits == 25 and prs == 8:  # Common mock values
                                            print(f"    ⚠️  Suspicious: Common mock values detected")
                                        
                                        # Check for timestamps or repo names that indicate real data
                                        if 'repositories' in member_data:
                                            repos = member_data['repositories']
                                            print(f"    📁 Repositories: {repos}")
                                            
                                        if 'latest_commit_date' in member_data:
                                            latest = member_data['latest_commit_date']
                                            print(f"    📅 Latest commit: {latest}")
                                            
                                            # Check if timestamp is recent (indicates real data)
                                            if latest and 'T' in str(latest):
                                                try:
                                                    commit_date = datetime.fromisoformat(latest.replace('Z', '+00:00'))
                                                    days_ago = (datetime.now().replace(tzinfo=commit_date.tzinfo) - commit_date).days
                                                    if days_ago <= 30:
                                                        print(f"    ✅ RECENT ACTIVITY ({days_ago} days ago) - DEFINITELY REAL DATA!")
                                                    else:
                                                        print(f"    📅 Activity from {days_ago} days ago")
                                                except:
                                                    pass
                                    else:
                                        print(f"    ❓ NO ACTIVITY - checking if this is real or mock...")
                                        
                                        # Even with 0 activity, we can tell if it's real by the structure
                                        if username == 'spencerhcheng':
                                            print(f"    ✅ Real GitHub API call but no recent activity in searched orgs")
                                            print(f"    💡 This could mean:")
                                            print(f"       - No commits in the date range ({start_date.date()} to {end_date.date()})")
                                            print(f"       - No commits in the organizations: {organizations}")
                                            print(f"       - Spencer might have activity in personal repos not being searched")
                                    
                                    # Check for rate limiting or errors
                                    if 'errors' in member_data:
                                        errors = member_data['errors']
                                        print(f"    ⚠️ Errors: {errors}")
                                        
                                        if 'rate_limited' in str(errors).lower():
                                            print(f"    🚨 RATE LIMITED!")
                                        
                                        if 'permission' in str(errors).lower() or 'forbidden' in str(errors).lower():
                                            print(f"    🔒 PERMISSION ERRORS!")
                                else:
                                    print(f"    Unexpected data: {member_data}")
                        
                        else:
                            print(f"  Unexpected data type: {github_data}")
                            
                        # Summary of findings
                        print(f"\n🔍 GITHUB DATA ANALYSIS:")
                        total_activity = sum(
                            (data.get('commits_count', 0) + data.get('pull_requests_count', 0) + data.get('reviews_count', 0))
                            for data in github_data.values() if isinstance(data, dict)
                        )
                        
                        if total_activity > 0:
                            print(f"  ✅ GitHub data collection is working! Total activity: {total_activity}")
                            print(f"  🔍 This suggests the issue is specific to Slack, not a general API problem.")
                        else:
                            print(f"  ❌ No GitHub activity found - could indicate:")
                            print(f"     1. Mock/fake data being used")
                            print(f"     2. Rate limiting issues")
                            print(f"     3. Permission problems")
                            print(f"     4. Genuinely inactive team members")
                            
                    except Exception as api_error:
                        print(f"❌ GitHub API call failed: {api_error}")
                        print(f"   Error type: {type(api_error)}")
                        
                        # Check if it's a rate limiting error
                        error_str = str(api_error).lower()
                        if 'rate' in error_str and 'limit' in error_str:
                            print("   🚨 This appears to be a RATE LIMITING issue!")
                        elif 'forbidden' in error_str or '403' in error_str:
                            print("   🔒 Permission/scope issue with GitHub token")
                        elif 'unauthorized' in error_str or '401' in error_str:
                            print("   🔑 Authentication issue with GitHub token")
                        
                        import traceback
                        traceback.print_exc()
                else:
                    print("❌ No team members found in recent analysis")
            else:
                print("❌ No recent analysis found to test with")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_github_api_direct())