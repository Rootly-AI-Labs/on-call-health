#!/usr/bin/env python3
"""
Test VADER sentiment analysis functionality
"""

def test_vader_sentiment():
    print("🔍 Testing VADER sentiment analysis...\n")
    
    try:
        # Test importing VADER
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        print("✅ Successfully imported vaderSentiment")
        
        # Initialize analyzer
        analyzer = SentimentIntensityAnalyzer()
        print("✅ Successfully initialized SentimentIntensityAnalyzer")
        
        # Test different sentiment types
        test_messages = [
            ("I love this project! Great work team!", "positive"),
            ("This is terrible and frustrating", "negative"), 
            ("The meeting is at 3pm", "neutral"),
            ("I'm feeling overwhelmed and stressed", "negative"),
            ("Thanks everyone for the help!", "positive"),
            ("", "empty")  # Edge case
        ]
        
        print("\n📊 Testing sentiment analysis on sample messages:\n")
        
        for message, expected in test_messages:
            if not message:
                print(f"Empty message: Skipping sentiment analysis")
                continue
                
            scores = analyzer.polarity_scores(message)
            compound = scores['compound']
            
            # Determine sentiment category
            if compound >= 0.05:
                category = "positive"
            elif compound <= -0.05:
                category = "negative"
            else:
                category = "neutral"
            
            print(f"Message: '{message[:50]}{'...' if len(message) > 50 else ''}'")
            print(f"  Compound: {compound:.3f}")
            print(f"  Category: {category} (expected: {expected})")
            print(f"  Full scores: {scores}")
            print()
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_slack_data():
    print("🔍 Checking Slack data in analysis results...\n")
    
    try:
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        from app.models.base import SessionLocal
        from sqlalchemy import text
        
        with SessionLocal() as db:
            # Check recent analysis with Slack data
            result = db.execute(text("""
                SELECT id, results
                FROM analyses 
                WHERE status = 'completed' 
                AND results IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 3
            """)).fetchall()
            
            if not result:
                print("❌ No completed analyses found")
                return
            
            import json
            for analysis in result:
                analysis_id = analysis[0]
                try:
                    results = json.loads(analysis[1])
                    print(f"📊 Analysis ID: {analysis_id}")
                    
                    # Check if there's Slack data
                    members = results.get('organization_members', [])
                    
                    slack_data_found = False
                    for member in members:
                        slack_activity = member.get('slack_activity')
                        if slack_activity and slack_activity != {}:
                            print(f"  👤 {member.get('user_name', 'Unknown')}")
                            print(f"    Sentiment Score: {slack_activity.get('sentiment_score', 'N/A')}")
                            print(f"    Messages: {slack_activity.get('messages_sent', 0)}")
                            print(f"    Avg Response Time: {slack_activity.get('avg_response_time_minutes', 0)}m")
                            slack_data_found = True
                            break
                    
                    if not slack_data_found:
                        print(f"  ❌ No Slack activity data found")
                    
                    # Check team-level Slack summary
                    team_summary = results.get('team_summary', {})
                    slack_summary = team_summary.get('slack_activity', {})
                    if slack_summary:
                        print(f"  📈 Team Slack Summary:")
                        print(f"    Avg Sentiment: {slack_summary.get('avg_sentiment_score', 'N/A')}")
                        print(f"    Overall Sentiment: {slack_summary.get('sentiment_analysis', {}).get('overall_sentiment', 'N/A')}")
                    
                    print()
                    
                except Exception as e:
                    print(f"  ❌ Error parsing analysis {analysis_id}: {e}")
                    
    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    # Test VADER functionality
    vader_works = test_vader_sentiment()
    
    if vader_works:
        print("=" * 50)
        # Test actual data
        test_slack_data()
    else:
        print("❌ VADER sentiment analysis is not working properly")