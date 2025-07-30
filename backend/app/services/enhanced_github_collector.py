"""
Enhanced GitHub collector that records mapping data.
"""
import logging
from typing import Dict, List, Optional
from .github_collector import collect_team_github_data as original_collect_team_github_data
from .mapping_recorder import MappingRecorder

logger = logging.getLogger(__name__)

async def collect_team_github_data_with_mapping(
    team_emails: List[str], 
    days: int = 30, 
    github_token: str = None,
    user_id: Optional[int] = None,
    analysis_id: Optional[int] = None,
    source_platform: str = "rootly"
) -> Dict[str, Dict]:
    """
    Enhanced version of collect_team_github_data that records mapping attempts.
    """
    recorder = MappingRecorder() if user_id else None
    
    # Phase 1.3: Track processed emails to prevent duplicates within this analysis session
    processed_emails = set()
    
    # Call original function
    github_data = await original_collect_team_github_data(team_emails, days, github_token)
    
    # Record mapping attempts if we have user context
    if recorder and user_id:
        for email in team_emails:
            # Phase 1.3: Skip if already processed in this session
            if email in processed_emails:
                logger.debug(f"Skipping {email} - already processed in this analysis session")
                continue
            processed_emails.add(email)
            if email in github_data:
                # Successful mapping
                data_points = 0
                user_data = github_data[email]
                
                # Count data points from actual GitHub data structure
                if isinstance(user_data, dict):
                    metrics = user_data.get("metrics", {})
                    data_points += metrics.get("total_commits", 0)
                    data_points += metrics.get("total_pull_requests", 0)
                    data_points += metrics.get("total_reviews", 0)
                
                # Try to extract the GitHub username from the data
                github_username = None
                
                # First, check predefined mappings
                from .github_collector import GitHubCollector
                collector = GitHubCollector()
                if email in collector.predefined_email_mappings:
                    github_username = collector.predefined_email_mappings[email]
                    logger.info(f"Found predefined mapping: {email} -> {github_username}")
                
                # If no predefined mapping, try to extract from data
                if not github_username:
                    if isinstance(user_data, dict) and "username" in user_data:
                        github_username = user_data["username"]
                    elif isinstance(user_data, dict) and "github_username" in user_data:
                        github_username = user_data["github_username"]
                
                if github_username:
                    # Determine mapping method based on how we found the username
                    if email in collector.predefined_email_mappings:
                        mapping_method = "predefined_mapping"
                    else:
                        mapping_method = "api_discovery"
                    
                    recorder.record_successful_mapping(
                        user_id=user_id,
                        analysis_id=analysis_id,
                        source_platform=source_platform,
                        source_identifier=email,
                        target_platform="github",
                        target_identifier=github_username,
                        mapping_method=mapping_method,
                        data_points_count=data_points
                    )
                    logger.info(f"✓ Recorded successful GitHub mapping: {email} -> {github_username} ({data_points} data points) via {mapping_method}")
                else:
                    # Data collected but no clear username
                    recorder.record_successful_mapping(
                        user_id=user_id,
                        analysis_id=analysis_id,
                        source_platform=source_platform,
                        source_identifier=email,
                        target_platform="github",
                        target_identifier="unknown",
                        mapping_method="api_collection",
                        data_points_count=data_points
                    )
                    logger.info(f"? Recorded GitHub data collection: {email} -> unknown user ({data_points} data points)")
            else:
                # Failed mapping
                recorder.record_failed_mapping(
                    user_id=user_id,
                    analysis_id=analysis_id,
                    source_platform=source_platform,
                    source_identifier=email,
                    target_platform="github",
                    error_message="No GitHub data found for email",
                    mapping_method="email_search"
                )
                logger.info(f"✗ Recorded failed GitHub mapping: {email} -> no data found")
    
    return github_data