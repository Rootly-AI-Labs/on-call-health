#!/usr/bin/env python3
"""
Slim down the mock_analysis_data.json by applying the slim_incidents function.
This reduces the file size by ~96% by removing unnecessary incident fields.
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional


def slim_user_object(user_obj: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Extract minimal user information from nested user object."""
    if not user_obj or not isinstance(user_obj, dict):
        return None

    # Handle both direct attributes and nested data structure
    if 'data' in user_obj:
        user_data = user_obj['data']
        if not user_data or not isinstance(user_data, dict):
            return None

        user_attrs = user_data.get('attributes', {})
        return {
            'id': user_data.get('id'),
            'email': user_attrs.get('email'),
            'name': user_attrs.get('name') or user_attrs.get('full_name')
        }
    else:
        # Already simplified structure - return as-is
        return user_obj


def extract_severity_name(severity_obj: Optional[Any]) -> Optional[str]:
    """Extract just the severity name (e.g., "SEV0", "SEV2") from complex nested object."""
    if not severity_obj:
        return None

    # Already a string
    if isinstance(severity_obj, str):
        return severity_obj

    # Extract from nested structure
    if isinstance(severity_obj, dict):
        if 'data' in severity_obj:
            sev_data = severity_obj['data']
            if isinstance(sev_data, dict) and 'attributes' in sev_data:
                return sev_data['attributes'].get('name')
        # Fallback: check if attributes at top level
        if 'attributes' in severity_obj:
            return severity_obj['attributes'].get('name')

    return None


def slim_incident(incident: Dict[str, Any]) -> Dict[str, Any]:
    """
    Slim down incident data from ~27KB to ~1-2KB by removing unnecessary fields.
    Reduction: 96-97% while preserving all fields used by the application.
    """
    if not incident or not isinstance(incident, dict):
        return incident

    attrs = incident.get('attributes', {})

    # Build slimmed incident preserving structure compatibility
    slimmed = {
        'id': incident.get('id'),
        'type': incident.get('type'),
        'attributes': {
            # Core incident fields
            'sequential_id': attrs.get('sequential_id'),
            'title': attrs.get('title'),
            'summary': attrs.get('summary'),
            'status': attrs.get('status'),
            'severity': extract_severity_name(attrs.get('severity')),

            # Timestamps
            'created_at': attrs.get('created_at'),
            'started_at': attrs.get('started_at'),
            'acknowledged_at': attrs.get('acknowledged_at'),
            'mitigated_at': attrs.get('mitigated_at'),
            'resolved_at': attrs.get('resolved_at'),

            # User objects (slimmed from 5KB to ~50 bytes each)
            'user': slim_user_object(attrs.get('user')),
            'started_by': slim_user_object(attrs.get('started_by')),
            'resolved_by': slim_user_object(attrs.get('resolved_by')),
            'mitigated_by': slim_user_object(attrs.get('mitigated_by')),

            # Slack integration
            'slack_channel_id': attrs.get('slack_channel_id'),
            'slack_channel_name': attrs.get('slack_channel_name'),
            'slack_channel_url': attrs.get('slack_channel_url'),
            'slack_channel_deep_link': attrs.get('slack_channel_deep_link'),
        }
    }

    # Remove None values to save additional space
    slimmed['attributes'] = {k: v for k, v in slimmed['attributes'].items() if v is not None}

    return slimmed


def slim_incidents(incidents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Slim down a list of incidents."""
    if not incidents:
        return incidents

    original_size = sum(len(str(inc)) for inc in incidents)
    slimmed = [slim_incident(inc) for inc in incidents]
    slimmed_size = sum(len(str(inc)) for inc in slimmed)

    reduction_pct = (1 - slimmed_size / original_size) * 100 if original_size > 0 else 0

    print(
        f"Slimmed {len(incidents)} incidents: "
        f"{original_size / 1024 / 1024:.2f} MB → {slimmed_size / 1024 / 1024:.2f} MB "
        f"({reduction_pct:.1f}% reduction)"
    )

    return slimmed


def main():
    mock_file = Path(__file__).parent / "mock_analysis_data.json"

    print(f"Loading mock data from {mock_file}")
    print(f"Original file size: {mock_file.stat().st_size / 1024 / 1024:.2f} MB")

    with open(mock_file, 'r') as f:
        data = json.load(f)

    # Check if raw_incident_data exists
    if 'analysis' in data and 'results' in data['analysis']:
        results = data['analysis']['results']

        if 'raw_incident_data' in results:
            original_incidents = results['raw_incident_data']
            print(f"Found {len(original_incidents)} incidents in raw_incident_data")

            # Apply slimming
            print("Applying slim_incidents() function...")
            slimmed_incidents = slim_incidents(original_incidents)

            # Replace in the data structure
            results['raw_incident_data'] = slimmed_incidents

            print(f"Slimmed to {len(slimmed_incidents)} incidents")
            print("Writing slimmed data back to file...")

            # Write back to file
            with open(mock_file, 'w') as f:
                json.dump(data, f, indent=2)

            new_size = mock_file.stat().st_size / 1024 / 1024
            print(f"New file size: {new_size:.2f} MB")
            print(f"File size reduction: {(1 - new_size / 7.1) * 100:.1f}%")
            print("✅ Mock data slimmed successfully!")
        else:
            print("❌ No raw_incident_data found in mock data")
    else:
        print("❌ Unexpected mock data structure")


if __name__ == "__main__":
    main()
