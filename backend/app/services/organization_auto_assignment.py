"""
Organization Auto-Assignment Service

Automatically assigns users to organizations based on their email domain when they sign up.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models.user import User
from ..models.organization import Organization

logger = logging.getLogger(__name__)

# Personal email domains that should NOT create organizations
PERSONAL_EMAIL_DOMAINS = {
    'gmail.com',
    'googlemail.com',
    'yahoo.com',
    'yahoo.co.uk',
    'yahoo.fr',
    'hotmail.com',
    'outlook.com',
    'live.com',
    'msn.com',
    'hey.com',
    'protonmail.com',
    'proton.me',
    'icloud.com',
    'me.com',
    'aol.com',
    'mail.com',
    'zoho.com',
    'yandex.com',
    'gmx.com',
}


def _extract_domain_from_email(email: str) -> str:
    """
    Extract domain from email address.

    Args:
        email: Email address

    Returns:
        str: Domain part of email (e.g., 'rootly.com' from 'user@rootly.com')
    """
    if '@' not in email:
        return ''
    return email.split('@')[1].lower()


def _is_personal_email_domain(domain: str) -> bool:
    """
    Check if domain is a personal email provider.

    Args:
        domain: Email domain

    Returns:
        bool: True if personal email provider, False otherwise
    """
    return domain.lower() in PERSONAL_EMAIL_DOMAINS


def _create_organization_from_domain(db: Session, domain: str, user: User) -> Organization:
    """
    Create a new organization from email domain.

    Args:
        db: Database session
        domain: Email domain (e.g., 'rootly.com')
        user: User who triggered the creation

    Returns:
        Organization: Newly created organization
    """
    # Extract company name from domain (e.g., 'rootly.com' -> 'Rootly')
    # Handle special cases like .edu, .ac.uk, etc.
    parts = domain.split('.')
    if len(parts) >= 2 and parts[-1] in ['edu', 'ac']:
        # For .edu or .ac domains, use the full name before TLD
        # e.g., 'mit.edu' -> 'Mit', 'oxford.ac.uk' -> 'Oxford'
        org_name = parts[0].capitalize()
    else:
        # For regular domains, use first part
        # e.g., 'rootly.com' -> 'Rootly'
        org_name = parts[0].capitalize()

    # Create slug from domain (replace dots with hyphens)
    slug = domain.replace('.', '-')

    org = Organization(
        name=org_name,
        domain=domain,
        slug=slug,
        status='active',
        plan_type='free',
        max_users=50,
        max_analyses_per_month=5,
    )

    db.add(org)
    db.commit()
    db.refresh(org)

    logger.info(f"Created new organization '{org_name}' (id={org.id}) for domain {domain}")
    return org


def assign_user_to_organization(db: Session, user: User) -> bool:
    """
    Automatically assign user to organization based on email domain.

    Logic:
    1. Personal email domains (gmail.com, yahoo.com, etc.) -> Stay org-less (NULL)
    2. Existing org with matching domain -> Auto-join as member
    3. New company domain (first user) -> Create new org, user becomes admin

    Args:
        db: Database session
        user: User to assign (must have valid email)

    Returns:
        bool: True if user was assigned to an organization, False if staying org-less
    """
    try:
        domain = _extract_domain_from_email(user.email)

        if not domain:
            logger.warning(f"Could not extract domain from email: {user.email}")
            return False

        # Check if personal email domain
        if _is_personal_email_domain(domain):
            logger.info(f"User {user.email} has personal email domain ({domain}), staying org-less")
            return False

        # Check if organization already exists for this domain
        existing_org = db.query(Organization).filter(
            Organization.domain == domain
        ).first()

        if existing_org:
            # Auto-join existing org as member
            user.organization_id = existing_org.id
            user.role = 'member'
            user.joined_org_at = datetime.now(timezone.utc)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User {user.email} auto-joined existing org '{existing_org.name}' (id={existing_org.id}) as member")
            return True

        # Create new org for this domain, user becomes admin
        try:
            new_org = _create_organization_from_domain(db, domain, user)
            user.organization_id = new_org.id
            user.role = 'admin'  # First user becomes admin
            user.is_super_admin = True  # First user becomes super admin
            user.joined_org_at = datetime.now(timezone.utc)
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"User {user.email} created new org '{new_org.name}' (id={new_org.id}) and became admin + super admin")
            return True
        except Exception as e:
            logger.error(f"Failed to create organization for domain {domain}: {e}")
            db.rollback()
            # User stays org-less on failure
            return False

    except Exception as e:
        logger.error(f"Failed to assign user {user.email} to organization: {e}", exc_info=True)
        # Don't raise - allow user registration to continue
        return False
