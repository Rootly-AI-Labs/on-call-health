"""
Account linking service for managing multiple OAuth providers and email addresses.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from ..models import User, OAuthProvider, UserEmail, Organization, OrganizationInvitation
from ..auth.oauth import github_oauth, google_oauth

logger = logging.getLogger(__name__)

class AccountLinkingService:
    """Service for linking OAuth accounts and managing user emails."""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def link_or_create_user(
        self, 
        provider: str, 
        user_info: Dict[str, Any], 
        access_token: str,
        refresh_token: Optional[str] = None
    ) -> Tuple[User, bool]:
        """
        Link OAuth provider to existing user or create new user.
        
        Returns:
            Tuple of (User, is_new_user)
        """
        provider_user_id = str(user_info.get("id"))
        
        # Get primary email only (no secondary emails)
        if provider == "github":
            all_emails = await github_oauth.get_all_emails(access_token)
            primary_email = github_oauth.select_primary_email(all_emails) or user_info.get("email")
            email_list = [primary_email]  # Only use primary email for user matching
            # Only store primary email (no secondary emails)
            primary_email_data = [{"email": primary_email, "verified": True, "primary": True}]
        elif provider == "google":
            # Google typically provides one verified email
            primary_email = user_info.get("email")
            email_list = [primary_email] if primary_email else []
            # Only store primary email
            primary_email_data = [{"email": primary_email, "verified": True, "primary": True}] if primary_email else []
        else:
            raise ValueError(f"Unsupported provider: {provider}")

        # DEBUG: Log the email being used for this OAuth login
        logger.info(f"OAuth {provider} login - primary_email: {primary_email}, user_info email: {user_info.get('email')}")

        if not primary_email:
            raise ValueError(f"No valid email found for {provider} user")

        # STRICT EMAIL-BASED MATCHING: Always check by primary email first (ignore OAuth provider history)
        logger.info(f"🔍 [EMAIL_CHECK] Checking if user exists with primary email: {primary_email}")

        # Look for existing user by primary email only
        existing_user = self._find_user_by_emails(email_list)
        
        if existing_user:
            try:
                # Link this provider to existing user
                logger.info(f"Linking {provider} account to existing user {existing_user.id}")
                self._link_provider_to_user(
                    existing_user, provider, provider_user_id,
                    access_token, refresh_token, user_info
                )
                self._add_emails_to_user(existing_user, primary_email_data, provider)

                # Check if user needs organization assignment (for existing users after migration)
                if not existing_user.organization_id:
                    try:
                        self._assign_user_to_organization(existing_user, primary_email)
                    except Exception as e:
                        logger.error(f"Error assigning user to organization: {e}")
                        # Rollback and continue without organization assignment
                        self.db.rollback()

                        # Retry the provider linking without organization assignment
                        self._link_provider_to_user(
                            existing_user, provider, provider_user_id,
                            access_token, refresh_token, user_info
                        )
                        self._add_emails_to_user(existing_user, primary_email_data, provider)

                self.db.commit()
                return existing_user, False

            except Exception as e:
                logger.error(f"Error linking provider to existing user: {e}")
                self.db.rollback()
                raise
        else:
            try:
                # Ensure we're not seeing stale data from previous transaction
                self.db.expire_all()  # Clear any cached data

                # Create new user
                logger.info(f"Creating new user for {provider} account with email: {primary_email}, name: {user_info.get('name')}")
                new_user = self._create_new_user(
                    primary_email, user_info.get("name"),
                    provider, provider_user_id, access_token, refresh_token
                )
                self._add_emails_to_user(new_user, primary_email_data, provider)
                return new_user, True

            except Exception as e:
                logger.error(f"Error creating new user: {e}")
                self.db.rollback()
                raise
    
    def _find_user_by_emails(self, email_list: List[str]) -> Optional[User]:
        """Find existing user by PRIMARY email only (not secondary emails)."""
        logger.info(f"🔍 [FIND_USER] Searching for user with PRIMARY emails: {email_list}")

        for email in email_list:
            # Check primary email ONLY (skip secondary emails)
            logger.info(f"🔍 [FIND_USER] Checking PRIMARY email: {email}")
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                logger.info(f"✅ [FIND_USER] MATCH! Found user {user.id} ({user.email}) by PRIMARY email: {email}")
                return user
            else:
                logger.info(f"❌ [FIND_USER] No primary email match for: {email}")

        logger.info(f"⭕ [FIND_USER] RESULT: No user found for PRIMARY emails: {email_list}")
        return None
    
    def _create_new_user(
        self,
        primary_email: str,
        name: Optional[str],
        provider: str,
        provider_user_id: str,
        access_token: str,
        refresh_token: Optional[str]
    ) -> User:
        """Create a new user with OAuth provider."""
        # Validate email is present and not from wrong source
        if not primary_email or '@' not in primary_email:
            raise ValueError(f"Invalid primary_email for new user: {primary_email}")

        # DEBUG: Confirm email being used for new user
        logger.info(f"_create_new_user called with primary_email={primary_email}, provider={provider}")

        user = User(
            email=primary_email,
            name=name,
            is_verified=True,
            # Legacy fields for backward compatibility
            provider=provider,
            provider_id=provider_user_id
        )
        user.update_email_domain()  # Set email_domain from email
        self.db.add(user)
        self.db.flush()  # Get user ID
        
        # Add OAuth provider
        oauth_provider = OAuthProvider(
            user_id=user.id,
            provider=provider,
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            is_primary=True
        )
        self.db.add(oauth_provider)
        
        # Add primary email
        user_email = UserEmail(
            user_id=user.id,
            email=primary_email,
            is_primary=True,
            is_verified=True,
            source=provider
        )
        self.db.add(user_email)

        # Handle organization assignment
        try:
            self._assign_user_to_organization(user, primary_email)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error assigning new user to organization: {e}")
            # Rollback and commit without organization assignment
            self.db.rollback()

            # Recreate user without organization assignment
            user = User(
                email=primary_email,
                name=name,
                is_verified=True,
                provider=provider,
                provider_id=provider_user_id
            )
            user.update_email_domain()  # Set email_domain from email
            self.db.add(user)
            self.db.flush()

            # Add OAuth provider
            oauth_provider = OAuthProvider(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                is_primary=True
            )
            self.db.add(oauth_provider)

            # Add primary email
            user_email = UserEmail(
                user_id=user.id,
                email=primary_email,
                is_primary=True,
                is_verified=True,
                source=provider
            )
            self.db.add(user_email)

            self.db.commit()

        return user
    
    def _link_provider_to_user(
        self,
        user: User,
        provider: str,
        provider_user_id: str,
        access_token: str,
        refresh_token: Optional[str],
        user_info: Dict[str, Any]
    ) -> None:
        """Link OAuth provider to user (unlinks from old user if needed)."""

        # Check if this OAuth provider (by provider + provider_user_id) is linked to ANY user
        existing_oauth = self.db.query(OAuthProvider).filter(
            OAuthProvider.provider == provider,
            OAuthProvider.provider_user_id == provider_user_id
        ).first()

        if existing_oauth:
            if existing_oauth.user_id == user.id:
                # Already linked to this user - just update tokens
                logger.info(f"✅ Updating existing {provider} OAuth link for user {user.id}")
                existing_oauth.access_token = access_token
                existing_oauth.refresh_token = refresh_token
                existing_oauth.updated_at = datetime.now()
            else:
                # Linked to a DIFFERENT user - unlink and relink to current user
                old_user_id = existing_oauth.user_id
                logger.info(f"🔄 Unlinking {provider} from user {old_user_id} and relinking to user {user.id}")

                # Update the OAuth record to point to new user
                existing_oauth.user_id = user.id
                existing_oauth.access_token = access_token
                existing_oauth.refresh_token = refresh_token
                existing_oauth.updated_at = datetime.now()
        else:
            # No existing link - create new one
            logger.info(f"➕ Creating new {provider} OAuth link for user {user.id}")
            is_primary = len(user.oauth_providers) == 0
            oauth_provider = OAuthProvider(
                user_id=user.id,
                provider=provider,
                provider_user_id=provider_user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                is_primary=is_primary
            )
            self.db.add(oauth_provider)

        # Update user name if not set
        if not user.name and user_info.get("name"):
            user.name = user_info["name"]

        self.db.commit()
    
    def _add_emails_to_user(
        self, 
        user: User, 
        email_data: List[Dict[str, Any]], 
        provider: str
    ) -> None:
        """Add emails from OAuth provider to user."""
        for email_info in email_data:
            email = email_info["email"]
            
            # Check if email already exists for this user
            existing = self.db.query(UserEmail).filter(
                UserEmail.user_id == user.id,
                UserEmail.email == email
            ).first()
            
            if not existing:
                user_email = UserEmail(
                    user_id=user.id,
                    email=email,
                    is_primary=email_info.get("primary", False) and email == user.email,
                    is_verified=email_info.get("verified", True),
                    source=provider
                )
                self.db.add(user_email)
        
        self.db.commit()
    
    def get_user_providers(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all OAuth providers for a user."""
        providers = self.db.query(OAuthProvider).filter(
            OAuthProvider.user_id == user_id
        ).all()
        
        return [
            {
                "id": p.id,
                "provider": p.provider,
                "is_primary": p.is_primary,
                "created_at": p.created_at,
                "updated_at": p.updated_at
            }
            for p in providers
        ]
    
    def get_user_emails(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all emails for a user."""
        emails = self.db.query(UserEmail).filter(
            UserEmail.user_id == user_id
        ).all()
        
        return [
            {
                "id": e.id,
                "email": e.email,
                "is_primary": e.is_primary,
                "is_verified": e.is_verified,
                "source": e.source,
                "created_at": e.created_at
            }
            for e in emails
        ]
    
    def unlink_provider(self, user_id: int, provider: str) -> bool:
        """Unlink an OAuth provider from user."""
        providers = self.db.query(OAuthProvider).filter(
            OAuthProvider.user_id == user_id
        ).all()
        
        # Don't allow unlinking if it's the only provider
        if len(providers) <= 1:
            return False
        
        provider_to_remove = self.db.query(OAuthProvider).filter(
            OAuthProvider.user_id == user_id,
            OAuthProvider.provider == provider
        ).first()
        
        if not provider_to_remove:
            return False
        
        # If removing primary provider, make another one primary
        if provider_to_remove.is_primary:
            remaining_provider = self.db.query(OAuthProvider).filter(
                OAuthProvider.user_id == user_id,
                OAuthProvider.provider != provider
            ).first()
            if remaining_provider:
                remaining_provider.is_primary = True
        
        self.db.delete(provider_to_remove)
        self.db.commit()
        return True

    def _assign_user_to_organization(self, user: User, email: str) -> None:
        """Assign user to organization based on email domain or invitation."""
        try:
            domain = email.split('@')[1] if '@' in email else None
            if not domain:
                logger.info(f"No domain found in email {email}")
                return

            # Shared domains (Gmail, etc.) - do NOT auto-accept invitations
            # Users must explicitly accept invitations via the invitation page
            shared_domains = {'gmail.com', 'googlemail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com', 'hey.com'}
            if domain in shared_domains:
                # Check for pending invitation (for logging purposes only)
                invitation = self.db.query(OrganizationInvitation).filter(
                    OrganizationInvitation.email == email,
                    OrganizationInvitation.status == 'pending'
                ).first()

                if invitation and not invitation.is_expired:
                    # DO NOT auto-accept - user must explicitly accept via /invitations/accept/{id}
                    logger.info(f"Pending invitation found for {email} to org {invitation.organization_id}, but NOT auto-accepting (user must accept manually)")
                else:
                    logger.info(f"No pending invitation found for {email}")
                # Leave user unassigned until they manually accept the invitation via the UI

            else:
                # Company domain - get or create organization
                organization = self.db.query(Organization).filter(
                    Organization.domain == domain
                ).first()

                if not organization:
                    # Auto-create organization for this domain
                    org_name = domain.split('.')[0].title()  # "xyz.com" → "Xyz"
                    org_slug = domain.replace('.', '-')  # "xyz.com" → "xyz-com"

                    organization = Organization(
                        name=org_name,
                        domain=domain,
                        slug=org_slug,
                        status='active'
                    )
                    self.db.add(organization)
                    self.db.flush()  # Get the ID
                    logger.info(f"Auto-created organization '{org_name}' (id={organization.id}) for domain {domain}")

                # Check if this is the first user from this domain (make them admin)
                existing_users = self.db.query(User).filter(
                    User.organization_id == organization.id,
                    User.status == 'active'
                ).count()

                user.organization_id = organization.id
                # First user is admin, subsequent users are members
                user.role = 'admin' if existing_users == 0 else 'member'
                user.joined_org_at = datetime.now()

                logger.info(f"Auto-assigned {email} to org {organization.id} ({organization.name}) as {user.role}")

        except Exception as e:
            logger.error(f"Error in _assign_user_to_organization: {e}")
            raise