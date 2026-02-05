"""
Checkpoint-aware Analysis Runner.

Refactored analysis execution with checkpoint/resume support for deployment resilience.
This module wraps the existing UnifiedBurnoutAnalyzer with checkpoint logic.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from ..models import (
    Analysis,
    User,
    RootlyIntegration,
    JiraIntegration,
    UserCorrelation,
    get_db,
)
from ..core.rootly_client import RootlyAPIClient
from ..services.slack_token_service import SlackTokenService
from ..services.unified_burnout_analyzer import UnifiedBurnoutAnalyzer
from .checkpoint import (
    save_checkpoint,
    load_checkpoint,
    clear_checkpoint,
    should_resume_from_checkpoint,
)

logger = logging.getLogger(__name__)

# Global state for graceful shutdown coordination
_shutdown_requested: bool = False
_current_analysis_id: Optional[int] = None


def request_shutdown() -> None:
    """Signal that shutdown has been requested (called by SIGTERM handler)."""
    global _shutdown_requested
    _shutdown_requested = True
    analysis_info = f"analysis {_current_analysis_id}" if _current_analysis_id else "no active analysis"
    logger.warning(f"Shutdown requested ({analysis_info})")


def check_shutdown() -> bool:
    """Check if shutdown has been requested."""
    return _shutdown_requested


async def run_analysis_with_checkpoints(
    analysis_id: int,
    integration_id: int,
    days_back: int,
    user_id: int,
    db: Optional[Session] = None,
) -> dict[str, Any]:
    """
    Run burnout analysis with checkpoint support.

    Phases with checkpoints:
        0: Starting (no checkpoint save - restart if interrupted)
        1: Data fetch complete (Rootly/PagerDuty data collected)
        2: All data collected (GitHub, Slack, Jira data added)
        3: Team analysis complete (burnout scores calculated, results saved)

    Args:
        analysis_id: Analysis database ID
        integration_id: Rootly/PagerDuty integration ID
        days_back: Number of days to analyze
        user_id: User ID requesting analysis
        db: Optional database session (creates new one if None)

    Returns:
        Dict with status and results

    Raises:
        Exception: On fatal errors (logged and analysis marked as failed)

    Security:
        - Validates all checkpoint data before saving
        - Limits checkpoint resume attempts to 3
        - Gracefully handles SIGTERM for deployment resilience
    """
    global _current_analysis_id, _shutdown_requested

    _current_analysis_id = analysis_id
    _shutdown_requested = False

    # Create DB session if not provided
    close_db = False
    if db is None:
        db = next(get_db())
        close_db = True

    try:
        # Load analysis record
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise Exception(f"Analysis {analysis_id} not found")

        # Check if we should resume from checkpoint
        checkpoint_data = await load_checkpoint(db, analysis_id)
        resume_from = 0

        if checkpoint_data and should_resume_from_checkpoint(checkpoint_data.get("checkpoint", 0)):
            resume_from = checkpoint_data.get("checkpoint", 0)
            logger.info(f"Resuming analysis {analysis_id} from checkpoint {resume_from}")

            # Increment attempt count (limit to 3 attempts)
            analysis.attempt_count = (analysis.attempt_count or 0) + 1
            if analysis.attempt_count > 3:
                raise Exception(f"Analysis exceeded maximum resume attempts (3)")
            db.commit()
        else:
            logger.info(f"Starting analysis {analysis_id} from beginning")
            # Reset attempt count
            analysis.attempt_count = 0
            db.commit()

        # Update status to running
        analysis.status = "running"
        db.commit()

        # Initialize checkpoint data structure
        if not checkpoint_data:
            checkpoint_data = {
                "checkpoint": 0,
                "collected_data": {},
                "intermediate_results": {},
                "phase_durations": {},
            }
        else:
            # Ensure all required keys exist when resuming
            checkpoint_data.setdefault("collected_data", {})
            checkpoint_data.setdefault("intermediate_results", {})
            checkpoint_data.setdefault("phase_durations", {})

        # ====================
        # CHECKPOINT 0: Starting
        # ====================
        phase_start = datetime.now()
        logger.info(f"CHECKPOINT 0: Analysis {analysis_id} starting")

        # Get the integration
        integration = db.query(RootlyIntegration).filter(
            RootlyIntegration.id == integration_id
        ).first()
        if not integration:
            raise Exception(f"Integration with ID {integration_id} not found")

        # Update last_used_at
        integration.last_used_at = datetime.now()
        db.commit()

        # Get user and check available integrations
        user = db.query(User).filter(User.id == user_id).first()
        has_llm_token = user and user.llm_token and user.llm_provider

        # Check for GitHub integration
        from ..models import GitHubIntegration
        github_integration = db.query(GitHubIntegration).filter(
            GitHubIntegration.user_id == user_id,
            GitHubIntegration.github_token.isnot(None),
        ).first()
        has_github = bool(github_integration)

        # Get Slack token
        slack_token = None
        slack_service = SlackTokenService(db)
        if user:
            slack_token = slack_service.get_oauth_token_for_user(user)

        # Check for Jira integration
        jira_integration = db.query(JiraIntegration).filter(
            JiraIntegration.user_id == user_id,
            JiraIntegration.access_token.isnot(None),
        ).first()
        has_jira = bool(jira_integration)

        # ====================
        # CHECKPOINT 1: Data Fetch
        # ====================
        if check_shutdown():
            await save_checkpoint(db, analysis_id, 0, checkpoint_data)
            return {"status": "interrupted", "checkpoint": 0}

        if resume_from < 1:
            logger.info(f"CHECKPOINT 0->1: Fetching incident data")
            phase_start = datetime.now()

            # Collect incident data
            client = RootlyAPIClient(integration.api_token)
            data = await client.collect_analysis_data(days_back=days_back)

            checkpoint_data["collected_data"]["users"] = data.get("users", [])
            checkpoint_data["collected_data"]["incidents"] = data.get("incidents", [])
            checkpoint_data["collected_data"]["metadata"] = data.get("collection_metadata", {})
            checkpoint_data["phase_durations"]["data_fetch"] = (datetime.now() - phase_start).total_seconds()

            await save_checkpoint(db, analysis_id, 1, checkpoint_data)
            logger.info(f"CHECKPOINT 1: Data fetch complete - {len(data.get('users', []))} users, {len(data.get('incidents', []))} incidents")
        else:
            logger.info(f"CHECKPOINT 1: Loaded cached data from checkpoint")
            data = {
                "users": checkpoint_data["collected_data"].get("users", []),
                "incidents": checkpoint_data["collected_data"].get("incidents", []),
                "collection_metadata": checkpoint_data["collected_data"].get("metadata", {}),
            }

        # ====================
        # CHECKPOINT 2: All Data Collected
        # ====================
        if check_shutdown():
            await save_checkpoint(db, analysis_id, 1, checkpoint_data)
            return {"status": "interrupted", "checkpoint": 1}

        # Decrypt tokens BEFORE checkpoint block - needed for both fresh runs and resume
        # (Cannot store decrypted tokens in checkpoint for security reasons)
        github_token = None
        if has_github:
            try:
                from ..api.endpoints.github import decrypt_token as decrypt_github_token
                github_token = decrypt_github_token(github_integration.github_token)
            except Exception as e:
                logger.error(f"Failed to decrypt GitHub token: {e}")

        jira_token = None
        if has_jira:
            try:
                from ..api.endpoints.jira import decrypt_jira_token
                jira_token = decrypt_jira_token(jira_integration.access_token)
            except Exception as e:
                logger.error(f"Failed to decrypt Jira token: {e}")

        if resume_from < 2:
            logger.info(f"CHECKPOINT 1->2: Collecting GitHub/Slack/Jira data")
            phase_start = datetime.now()

            # Collect additional data sources
            github_data = None
            if has_github and github_token:
                try:
                    from ..services.github_collector import collect_team_github_data

                    # Get team emails from user correlations
                    mappings = db.query(UserCorrelation).filter(
                        UserCorrelation.organization_id == user.organization_id
                    ).all()
                    team_emails = [uc.email for uc in mappings if uc.email]

                    if team_emails:
                        github_data = await collect_team_github_data(team_emails, days_back, github_token)
                except Exception as e:
                    logger.error(f"Failed to collect GitHub data: {e}")

            # Fetch user correlations for Jira mapping
            synced_users = []
            try:
                user_correlations = db.query(UserCorrelation).filter(
                    UserCorrelation.organization_id == user.organization_id
                ).all()

                synced_users = [
                    {
                        "email": uc.email,
                        "name": uc.name,
                        "github_username": uc.github_username,
                        "slack_user_id": uc.slack_user_id,
                        "rootly_user_id": uc.rootly_user_id,
                        "jira_account_id": uc.jira_account_id,
                        "jira_email": uc.jira_email,
                    }
                    for uc in user_correlations
                ]
            except Exception as e:
                logger.error(f"Failed to fetch user correlations: {e}")

            checkpoint_data["collected_data"]["github_data"] = github_data
            checkpoint_data["collected_data"]["synced_users"] = synced_users
            checkpoint_data["collected_data"]["slack_token"] = bool(slack_token)
            checkpoint_data["collected_data"]["jira_token"] = bool(jira_token)
            checkpoint_data["phase_durations"]["additional_data_collection"] = (
                datetime.now() - phase_start
            ).total_seconds()

            await save_checkpoint(db, analysis_id, 2, checkpoint_data)
            logger.info(f"CHECKPOINT 2: All data collected")
        else:
            logger.info(f"CHECKPOINT 2: Loaded cached additional data")
            github_data = checkpoint_data["collected_data"].get("github_data")
            synced_users = checkpoint_data["collected_data"].get("synced_users", [])

        # ====================
        # CHECKPOINT 3: Team Analysis
        # ====================
        if check_shutdown():
            await save_checkpoint(db, analysis_id, 2, checkpoint_data)
            return {"status": "interrupted", "checkpoint": 2}

        if resume_from < 3:
            logger.info(f"CHECKPOINT 2->3: Running team burnout analysis")
            phase_start = datetime.now()

            # Set user context for AI analysis if available
            if has_llm_token:
                from ..services.ai_burnout_analyzer import set_user_context
                set_user_context(user)

            # Initialize analyzer
            analyzer = UnifiedBurnoutAnalyzer(
                api_token=integration.api_token,
                platform=integration.platform,
                enable_ai=has_llm_token,
                github_token=github_token,
                slack_token=slack_token,
                jira_token=jira_token,
                synced_users=synced_users,
                current_user_id=user_id,
            )

            # Run analysis
            results = await analyzer.analyze_burnout(
                time_range_days=days_back,
                include_weekends=True,
                user_id=user.id,
                analysis_id=analysis_id,
            )

            checkpoint_data["intermediate_results"]["analysis_results"] = results
            checkpoint_data["phase_durations"]["team_analysis"] = (datetime.now() - phase_start).total_seconds()

            await save_checkpoint(db, analysis_id, 3, checkpoint_data)
            logger.info(f"CHECKPOINT 3: Team analysis complete")
        else:
            logger.info(f"CHECKPOINT 3: Loaded cached analysis results")
            results = checkpoint_data["intermediate_results"].get("analysis_results", {})

        # ====================
        # CHECKPOINT COMPLETE
        # ====================
        logger.info(f"CHECKPOINT 3->COMPLETE: Analysis {analysis_id} finishing")

        # Save final results
        analysis.status = "completed"
        analysis.results = results
        analysis.completed_at = datetime.now()
        db.commit()

        # Clear checkpoint data (no longer needed)
        await clear_checkpoint(db, analysis_id)

        logger.info(f"Analysis {analysis_id} completed successfully")

        return {
            "status": "completed",
            "analysis_id": analysis_id,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Analysis {analysis_id} failed: {e}", exc_info=True)

        # Mark analysis as failed
        try:
            analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
            if analysis:
                analysis.status = "failed"
                analysis.error_message = str(e)
                db.commit()
        except Exception as commit_error:
            logger.error(f"Failed to mark analysis as failed: {commit_error}")

        raise

    finally:
        _current_analysis_id = None
        _shutdown_requested = False
        if close_db:
            db.close()


__all__ = ["run_analysis_with_checkpoints", "request_shutdown", "check_shutdown"]
