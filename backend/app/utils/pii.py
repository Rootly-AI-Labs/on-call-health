"""
PII (Personally Identifiable Information) utilities for data masking.
"""


def mask_email(email: str) -> str:
    """
    Mask email for logging to protect PII.
    Shows first 2 chars of local part and full domain.

    Examples:
        john.doe@example.com -> jo******@example.com
        ab@example.com -> **@example.com
        a@example.com -> *@example.com
        None or invalid -> ***
    """
    if not email or '@' not in email:
        return '***'
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return f"{'*' * len(local)}@{domain}"
    return f"{local[:2]}{'*' * (len(local) - 2)}@{domain}"
