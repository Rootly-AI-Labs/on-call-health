"""Platform-specific error messages for token validation failures."""

JIRA_ERROR_MESSAGES = {
    "authentication": {
        "message": "Invalid Jira Personal Access Token. The token may be expired or incorrectly entered.",
        "help_url": "https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
        "action": "Generate a new token in Atlassian Account Settings > Security > API Tokens"
    },
    "permissions": {
        "message": "Your Jira token lacks required permissions to access issue data.",
        "help_url": "https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
        "action": "Ensure your Atlassian account has read access to the projects you want to analyze"
    },
    "network": {
        "message": "Cannot reach Jira API. Check your network connection or site URL.",
        "action": "Verify you can access your Jira site in a browser and the URL is correct"
    },
    "format": {
        "message": "Invalid token format. Jira API tokens should be alphanumeric.",
        "action": "Copy the token exactly as shown in Atlassian Account Settings"
    },
    "site_url": {
        "message": "Invalid Jira site URL. URL must be a valid Atlassian Cloud URL.",
        "action": "Enter your Jira site URL in format: https://yourcompany.atlassian.net"
    }
}

LINEAR_ERROR_MESSAGES = {
    "authentication": {
        "message": "Invalid Linear Personal API Key. The key may be expired or incorrectly entered.",
        "help_url": "https://linear.app/settings/account/api",
        "action": "Generate a new API key in Linear Settings > Account > API > Personal API Keys"
    },
    "permissions": {
        "message": "Your Linear API key lacks required scopes. Ensure read access is enabled.",
        "help_url": "https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
        "action": "Create a new API key with at least read:issue and read:user scopes"
    },
    "network": {
        "message": "Cannot reach Linear API. Check your network connection.",
        "action": "Verify you can access linear.app in a browser"
    },
    "format": {
        "message": "Invalid API key format. Linear API keys start with 'lin_api_'.",
        "action": "Copy the API key exactly as shown in Linear Settings"
    }
}


def get_error_response(provider: str, error_type: str) -> dict:
    """Get platform-specific error response for a validation failure.

    Args:
        provider: 'jira' or 'linear'
        error_type: One of 'authentication', 'permissions', 'network', 'format', 'site_url'

    Returns:
        dict with 'message', optional 'help_url', and 'action' fields
    """
    error_maps = {
        "jira": JIRA_ERROR_MESSAGES,
        "linear": LINEAR_ERROR_MESSAGES
    }

    provider_map = error_maps.get(provider, {})
    error_info = provider_map.get(error_type, {
        "message": f"Token validation failed for {provider}.",
        "action": f"Please check your {provider} token and try again."
    })

    return {
        "error_type": error_type,
        **error_info
    }
