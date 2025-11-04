"""
Service for syncing all users from Rootly/PagerDuty to UserCorrelation table.
Ensures all team members can submit burnout surveys regardless of incident involvement.
"""
import logging
from typing import Dict, List, Any
from sqlalchemy.orm import Session
from app.models import User, UserCorrelation, RootlyIntegration
from app.core.rootly_client import RootlyAPIClient
from app.core.pagerduty_client import PagerDutyAPIClient

logger = logging.getLogger(__name__)


class UserSyncService:
    """Service to sync all users from integrations to UserCorrelation table."""

    def __init__(self, db: Session):
        self.db = db

    async def sync_integration_users(
        self,
        integration_id: int,
        current_user: User
    ) -> Dict[str, Any]:
        """
        Sync all users from a Rootly/PagerDuty integration to UserCorrelation.

        Args:
            integration_id: The integration to sync from
            current_user: The user who owns this integration

        Returns:
            Dictionary with sync statistics
        """
        try:
            # Get the integration
            integration = self.db.query(RootlyIntegration).filter(
                RootlyIntegration.id == integration_id,
                RootlyIntegration.user_id == current_user.id
            ).first()

            if not integration:
                raise ValueError(f"Integration {integration_id} not found")

            # Fetch users from the platform
            if integration.platform == "rootly":
                users = await self._fetch_rootly_users(integration.api_token)
            elif integration.platform == "pagerduty":
                users = await self._fetch_pagerduty_users(integration.api_token)
            else:
                raise ValueError(f"Unsupported platform: {integration.platform}")

            # Sync users to UserCorrelation
            stats = self._sync_users_to_correlation(
                users=users,
                platform=integration.platform,
                current_user=current_user,
                integration_id=str(integration_id)  # Store which integration synced this user
            )

            logger.info(
                f"Synced {stats['created']} new users, updated {stats['updated']} existing users "
                f"from {integration.platform} integration {integration_id}"
            )

            return stats

        except Exception as e:
            logger.error(f"Error syncing integration users: {e}")
            raise

    async def _fetch_rootly_users(self, api_token: str) -> List[Dict[str, Any]]:
        """Fetch all users from Rootly API."""
        client = RootlyAPIClient(api_token)
        raw_users = await client.get_users(limit=10000)  # Fetch up to 1000 users

        # Extract from JSONAPI format
        users = []
        for user in raw_users:
            attrs = user.get("attributes", {})
            users.append({
                "id": user.get("id"),
                "email": attrs.get("email"),
                "name": attrs.get("name") or attrs.get("full_name"),
                "platform": "rootly"
            })

        return users

    async def _fetch_pagerduty_users(self, api_token: str) -> List[Dict[str, Any]]:
        """Fetch all users from PagerDuty API."""
        client = PagerDutyAPIClient(api_token)
        raw_users = await client.get_users(limit=10000)

        # PagerDuty format (may need adjustment based on actual API response)
        users = []
        for user in raw_users:
            users.append({
                "id": user.get("id"),
                "email": user.get("email"),
                "name": user.get("name"),
                "platform": "pagerduty"
            })

        return users

    def _sync_users_to_correlation(
        self,
        users: List[Dict[str, Any]],
        platform: str,
        current_user: User,
        integration_id: str = None
    ) -> Dict[str, int]:
        """
        Sync users to UserCorrelation table.

        Creates new records or updates existing ones.
        Uses organization_id for multi-tenancy support.
        """
        created = 0
        updated = 0
        skipped = 0

        # Use organization_id for multi-tenancy (fallback to user_id for beta mode)
        organization_id = current_user.organization_id
        user_id = current_user.id

        # Beta mode: If no organization, isolate by user_id instead
        if not organization_id:
            logger.info(f"User {user_id} has no organization_id - using user_id for isolation (beta mode)")

        for user in users:
            email = user.get("email")
            if not email:
                skipped += 1
                logger.warning(f"Skipping user {user.get('id')} - no email")
                continue

            email = email.lower().strip()

            # Check if correlation already exists
            # Check by (user_id, email) to match the unique constraint
            correlation = self.db.query(UserCorrelation).filter(
                UserCorrelation.user_id == user_id,
                UserCorrelation.email == email
            ).first()

            if correlation:
                # Update existing correlation
                updated += self._update_correlation(correlation, user, platform, integration_id)
            else:
                # Create new correlation
                correlation = UserCorrelation(
                    user_id=current_user.id,  # Keep for backwards compatibility
                    organization_id=organization_id,  # Multi-tenancy key
                    email=email,
                    name=user.get("name"),  # Store user's display name
                    integration_ids=[integration_id] if integration_id else []  # Initialize array
                )
                self._update_correlation(correlation, user, platform, integration_id)
                self.db.add(correlation)
                created += 1

        # Commit all changes
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error committing user sync: {e}")
            raise

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total": len(users)
        }

    def _update_correlation(
        self,
        correlation: UserCorrelation,
        user: Dict[str, Any],
        platform: str,
        integration_id: str = None
    ) -> int:
        """
        Update a UserCorrelation record with platform-specific data.
        Returns 1 if updated, 0 if no changes.
        """
        updated = False

        # Update integration_ids array - add if not already present
        if integration_id:
            if not correlation.integration_ids:
                correlation.integration_ids = [integration_id]
                updated = True
            elif integration_id not in correlation.integration_ids:
                correlation.integration_ids = correlation.integration_ids + [integration_id]
                updated = True

        # Update name if available and different
        if user.get("name") and correlation.name != user["name"]:
            correlation.name = user["name"]
            updated = True

        if platform == "rootly":
            if not correlation.rootly_email or correlation.rootly_email != user["email"]:
                correlation.rootly_email = user["email"]
                updated = True
        elif platform == "pagerduty":
            if not correlation.pagerduty_user_id or correlation.pagerduty_user_id != user["id"]:
                correlation.pagerduty_user_id = user["id"]
                updated = True

        return 1 if updated else 0

    def sync_users_from_list(
        self,
        users: List[Dict[str, Any]],
        platform: str,
        current_user: User,
        integration_id: str = None
    ) -> Dict[str, int]:
        """
        Public method to sync a list of users to UserCorrelation.

        Used for beta integrations or when users are already fetched externally.

        Args:
            users: List of user dictionaries with id, email, name
            platform: "rootly" or "pagerduty"
            current_user: The user syncing these members
            integration_id: Optional integration identifier

        Returns:
            Dictionary with sync statistics
        """
        return self._sync_users_to_correlation(
            users=users,
            platform=platform,
            current_user=current_user,
            integration_id=integration_id
        )

    async def sync_all_integrations(self, current_user: User) -> Dict[str, Any]:
        """
        Sync users from ALL of the user's integrations.

        Useful for initial setup or bulk sync.
        """
        integrations = self.db.query(RootlyIntegration).filter(
            RootlyIntegration.user_id == current_user.id,
            RootlyIntegration.is_active == True
        ).all()

        total_stats = {
            "integrations_synced": 0,
            "total_created": 0,
            "total_updated": 0,
            "total_skipped": 0,
            "errors": []
        }

        for integration in integrations:
            try:
                stats = await self.sync_integration_users(
                    integration_id=integration.id,
                    current_user=current_user
                )
                total_stats["integrations_synced"] += 1
                total_stats["total_created"] += stats["created"]
                total_stats["total_updated"] += stats["updated"]
                total_stats["total_skipped"] += stats["skipped"]
            except Exception as e:
                error_msg = f"Failed to sync integration {integration.id}: {str(e)}"
                logger.error(error_msg)
                total_stats["errors"].append(error_msg)

        return total_stats