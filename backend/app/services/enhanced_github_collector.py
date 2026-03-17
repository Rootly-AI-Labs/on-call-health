"""
Enhanced GitHub collector that records mapping data with smart caching.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import or_, and_

from .mapping_recorder import MappingRecorder

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

async def collect_team_github_data_with_mapping(
    team_emails: List[str],
    days: int = 30,
    github_token: str = None,
    user_id: Optional[int] = None,
    analysis_id: Optional[int] = None,
    source_platform: str = "rootly",
    email_to_name: Optional[Dict[str, str]] = None,
    db: Optional["Session"] = None,
    org_id: Optional[int] = None
) -> Dict[str, Dict]:
    """
    Collect GitHub data for team members who have synced GitHub usernames.

    This function pre-filters users by checking UserCorrelation.github_username
    to avoid unnecessary API calls for users without GitHub mappings.

    Performance optimization:
    - Queries UserCorrelation once for all team emails
    - Only processes emails with github_username NOT NULL
    - Skips unmapped users entirely (no API calls)

    Args:
        team_emails: List of team member emails to process
        days: Number of days of GitHub activity to collect
        github_token: GitHub API token for authentication
        user_id: User ID for mapping context
        analysis_id: Analysis ID for tracking
        source_platform: Platform the emails came from (e.g., "rootly")
        email_to_name: Optional mapping of emails to full names
        db: Database session
        org_id: Organization ID for multi-tenancy isolation

    Returns:
        Dict mapping email -> github_data (only for users with mappings)
    """
    # Phase 2: Check if smart caching is enabled
    use_smart_caching = os.getenv('USE_SMART_GITHUB_CACHING', 'true').lower() == 'true'

    # PRE-FILTERING: Query UserCorrelation to find emails with GitHub mappings
    # This optimization skips unmapped users entirely, avoiding unnecessary API calls
    emails_to_process = set(team_emails)  # Default: process all emails

    if user_id and db:
        from ..models import UserCorrelation

        # Reuse passed db session or create new one if not provided/invalid
        session_to_use = db
        should_close = False
        if session_to_use is None:
            from ..models import SessionLocal
            session_to_use = SessionLocal()
            should_close = True

        try:
            # Query UserCorrelation for synced GitHub usernames
            # Filter by organization to prevent cross-org data leakage
            if org_id:
                user_correlations = session_to_use.query(UserCorrelation).filter(
                    UserCorrelation.email.in_(team_emails),
                    UserCorrelation.github_username.isnot(None),
                    or_(
                        UserCorrelation.user_id == user_id,  # Personal mappings
                        and_(
                            UserCorrelation.user_id.is_(None),
                            UserCorrelation.organization_id == org_id
                        )  # Team roster mappings
                    )
                ).all()
            else:
                # Fallback: no organization filter if org_id not provided (backward compatibility)
                user_correlations = session_to_use.query(UserCorrelation).filter(
                    UserCorrelation.email.in_(team_emails),
                    UserCorrelation.github_username.isnot(None)
                ).all()

            # Extract emails with GitHub mappings
            emails_with_github = {uc.email for uc in user_correlations if uc.email is not None}
            emails_without_github = set(team_emails) - emails_with_github

            # Log filtering results for transparency
            logger.info(
                f"📊 [GITHUB_FILTER] Team: {len(team_emails)} members total, "
                f"{len(emails_with_github)} with GitHub mappings, "
                f"{len(emails_without_github)} skipped (no mapping)"
            )

            # Only process emails with GitHub mappings
            if emails_with_github:
                emails_to_process = emails_with_github
            else:
                logger.warning(f"💻 GitHub: No synced usernames found in UserCorrelation for any team member")
                emails_to_process = set()  # Skip all users
        finally:
            if should_close:
                session_to_use.close()

    # If no emails to process after filtering, return empty dict
    if not emails_to_process:
        logger.info(f"💻 [GITHUB_FILTER] No emails to process after filtering, returning empty result")
        return {}

    # Convert back to list for processing
    filtered_team_emails = list(emails_to_process)

    if use_smart_caching and user_id:
        try:
            from .github_mapping_service import GitHubMappingService
            mapping_service = GitHubMappingService(db=db)
            return await mapping_service.get_smart_github_data(
                team_emails=filtered_team_emails,  # Use pre-filtered emails
                days=days,
                github_token=github_token,
                user_id=user_id,
                analysis_id=analysis_id,
                source_platform=source_platform,
                email_to_name=email_to_name
            )
        except Exception as e:
            logger.error(f"💻 GitHub: Smart caching failed: {e}")
            # Fall through to original logic with filtered emails
    recorder = MappingRecorder(db=db) if user_id else None

    # Phase 1.3: Track processed emails to prevent duplicates within this analysis session
    processed_emails = set()

    # Call original function with user_id for manual mapping support
    # Pass email_to_name mapping for better GitHub username matching
    from .github_collector import GitHubCollector
    collector = GitHubCollector()
    github_data = {}

    logger.info(f"💻 [GITHUB_COLLECTION] Starting collection for {len(filtered_team_emails)} team members (after pre-filtering)")

    success_count = 0
    failure_count = 0
    correlation_failures = 0
    api_failures = 0

    for email in filtered_team_emails:
        try:
            # Get full name for this email if available
            full_name = email_to_name.get(email) if email_to_name else None

            # Collect data with full name for better matching
            user_data = await collector.collect_github_data_for_user(
                email, days, github_token, user_id, full_name=full_name
            )
            if user_data:
                github_data[email] = user_data
                success_count += 1
            else:
                failure_count += 1
                # Check if it was a correlation failure or API failure by looking at logs
                # Since we don't have the failure reason here, we'll just count total failures
        except Exception as e:
            logger.error(f"❌ [GITHUB_COLLECTION_ERROR] Failed to collect GitHub data for {email}: {e}")
            failure_count += 1

    logger.info(f"📊 [GITHUB_COLLECTION_SUMMARY] Processed {len(filtered_team_emails)} members: {success_count} succeeded, {failure_count} failed")

    # Log final rate limit status
    if github_token:
        try:
            import aiohttp
            headers = {'Authorization': f'token {github_token}'}
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.github.com/rate_limit", headers=headers) as resp:
                    if resp.status == 200:
                        rate_data = await resp.json()
                        remaining = rate_data['rate']['remaining']
                        reset_time = rate_data['rate']['reset']
                        logger.info(f"GITHUB API: Rate limit remaining: {remaining}, resets at {datetime.fromtimestamp(reset_time)}")
        except Exception as e:
            logger.debug(f"Could not log final GitHub rate limit: {e}")

    # Record mapping attempts if we have user context
    if recorder and user_id:
        for email in team_emails:
            # Phase 1.3: Skip if already processed in this session
            if email in processed_emails:
                logger.debug(f"Skipping {email} - already processed in this analysis session")
                continue
            processed_emails.add(email)

            # Check if this email was skipped due to no mapping
            if email not in emails_to_process:
                # Email was pre-filtered (no GitHub mapping in UserCorrelation)
                member_user_id, org_id = recorder.get_user_and_org_for_email(email, analysis_id)
                recorder.record_failed_mapping(
                    user_id=member_user_id,
                    organization_id=org_id,
                    analysis_id=analysis_id,
                    source_platform=source_platform,
                    source_identifier=email,
                    target_platform="github",
                    error_message="No GitHub mapping found in UserCorrelation (skipped)",
                    mapping_method="pre_filter_skip"
                )
                continue

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

                # Extract from data
                if isinstance(user_data, dict) and "username" in user_data:
                    github_username = user_data["username"]
                elif isinstance(user_data, dict) and "github_username" in user_data:
                    github_username = user_data["github_username"]

                # Look up user_id and organization_id for this specific email
                member_user_id, org_id = recorder.get_user_and_org_for_email(email, analysis_id)

                if github_username:
                    # All mappings are now discovered via API
                    mapping_method = "api_discovery"

                    recorder.record_successful_mapping(
                        user_id=member_user_id,  # NULL if team member hasn't logged in
                        organization_id=org_id,
                        analysis_id=analysis_id,
                        source_platform=source_platform,
                        source_identifier=email,
                        target_platform="github",
                        target_identifier=github_username,
                        mapping_method=mapping_method,
                        data_points_count=data_points
                    )
                    logger.debug(f"GitHub: {email} -> {github_username} ({data_points} data points)")
                else:
                    # Data collected but no clear username
                    recorder.record_successful_mapping(
                        user_id=member_user_id,
                        organization_id=org_id,
                        analysis_id=analysis_id,
                        source_platform=source_platform,
                        source_identifier=email,
                        target_platform="github",
                        target_identifier="unknown",
                        mapping_method="api_collection",
                        data_points_count=data_points
                    )
            else:
                # Look up user_id and organization_id for failed mapping too
                member_user_id, org_id = recorder.get_user_and_org_for_email(email, analysis_id)

                # Failed mapping
                recorder.record_failed_mapping(
                    user_id=member_user_id,
                    organization_id=org_id,
                    analysis_id=analysis_id,
                    source_platform=source_platform,
                    source_identifier=email,
                    target_platform="github",
                    error_message="No GitHub data found for email",
                    mapping_method="email_search"
                )
    
    return github_data