"""
Mock Data Loader for Testing
Loads YAML scenario files and transforms them into the format expected by UnifiedBurnoutAnalyzer
"""
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MockDataLoader:
    """
    Loads mock data from YAML scenario files and formats it to match
    the structure returned by Rootly/PagerDuty APIs
    """

    def __init__(self, scenarios_dir: Optional[str] = None):
        """
        Initialize the mock data loader

        Args:
            scenarios_dir: Path to directory containing YAML scenario files.
                          Defaults to tests/mock_data/scenarios/
        """
        if scenarios_dir is None:
            # Default to scenarios directory relative to this file
            self.scenarios_dir = Path(__file__).parent / "scenarios"
        else:
            self.scenarios_dir = Path(scenarios_dir)

        if not self.scenarios_dir.exists():
            raise FileNotFoundError(f"Scenarios directory not found: {self.scenarios_dir}")

        logger.info(f"MockDataLoader initialized with scenarios from: {self.scenarios_dir}")

    def list_scenarios(self) -> List[str]:
        """
        List all available scenario names

        Returns:
            List of scenario names (without .yaml extension)
        """
        yaml_files = self.scenarios_dir.glob("*.yaml")
        return [f.stem for f in yaml_files]

    def load_scenario(self, scenario_name: str) -> Dict[str, Any]:
        """
        Load a scenario YAML file and return the raw data

        Args:
            scenario_name: Name of the scenario (without .yaml extension)

        Returns:
            Dictionary containing the scenario data

        Raises:
            FileNotFoundError: If scenario file doesn't exist
        """
        yaml_file = self.scenarios_dir / f"{scenario_name}.yaml"

        if not yaml_file.exists():
            available = ", ".join(self.list_scenarios())
            raise FileNotFoundError(
                f"Scenario '{scenario_name}' not found. "
                f"Available scenarios: {available}"
            )

        logger.info(f"Loading scenario: {scenario_name}")

        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        logger.info(f"Loaded {len(data.get('users', []))} users and {len(data.get('incidents', []))} incidents")
        return data

    def get_unified_data(
        self,
        scenario_name: str,
        platform: str = "rootly"
    ) -> Dict[str, Any]:
        """
        Get formatted data for UnifiedBurnoutAnalyzer
        This is the main method that should be called to get mock data

        Args:
            scenario_name: Name of the scenario to load
            platform: "rootly" or "pagerduty" - determines output format

        Returns:
            Dictionary matching the structure from _fetch_analysis_data()
            {
                "users": [...],
                "incidents": [...],
                "collection_metadata": {...}
            }
        """
        scenario_data = self.load_scenario(scenario_name)

        formatted_data = {
            "users": self._format_users(scenario_data['users'], platform),
            "incidents": self._format_incidents(scenario_data.get('incidents', []), platform),
            "collection_metadata": {
                "total_users": len(scenario_data['users']),
                "total_incidents": len(scenario_data.get('incidents', [])),
                "source": "mock_data",
                "scenario": scenario_name,
                "platform": platform,
                "loaded_at": datetime.now().isoformat()
            }
        }

        logger.info(f"Formatted data for {platform}: {len(formatted_data['users'])} users, {len(formatted_data['incidents'])} incidents")
        return formatted_data

    def _format_users(self, yaml_users: List[Dict], platform: str) -> List[Dict]:
        """
        Transform YAML user data into the structure expected by the analyzer

        Args:
            yaml_users: List of users from YAML file
            platform: "rootly" or "pagerduty"

        Returns:
            List of users in API format
        """
        formatted_users = []

        for user in yaml_users:
            if platform == "pagerduty":
                # PagerDuty API format
                formatted_user = {
                    "id": user.get('pagerduty', {}).get('id', user['email']),
                    "name": user['name'],
                    "email": user['email'],
                    "timezone": user.get('pagerduty', {}).get('timezone', 'UTC'),
                    "role": user.get('pagerduty', {}).get('role', 'user'),
                    "source": "pagerduty",
                    "job_title": user.get('pagerduty', {}).get('job_title'),
                    "teams": user.get('pagerduty', {}).get('teams', []),
                    "contact_methods_count": user.get('pagerduty', {}).get('contact_methods_count', 0)
                }
            else:
                # Rootly API format (JSON:API structure)
                rootly_data = user.get('rootly', {})
                formatted_user = {
                    "id": rootly_data.get('id', user['email']),
                    "type": "users",
                    "attributes": {
                        "name": user['name'],
                        "email": user['email'],
                        "full_name": user['name'],
                        "full_name_with_team": rootly_data.get('full_name_with_team', user['name']),
                        "slack_id": rootly_data.get('slack_id', ''),
                        "time_zone": rootly_data.get('time_zone', 'UTC'),
                        "phone": rootly_data.get('phone', ''),
                        "created_at": rootly_data.get('created_at', ''),
                        "updated_at": rootly_data.get('updated_at', '')
                    },
                    "relationships": {
                        "email_addresses": {"data": []},
                        "phone_numbers": {"data": []},
                        "devices": {"data": []},
                        "role": {"data": {}},
                        "on_call_role": {"data": {}}
                    }
                }

            formatted_users.append(formatted_user)

        return formatted_users

    def _format_incidents(self, yaml_incidents: List[Dict], platform: str) -> List[Dict]:
        """
        Transform YAML incident data into API format

        Args:
            yaml_incidents: List of incidents from YAML file
            platform: "rootly" or "pagerduty"

        Returns:
            List of incidents in API format
        """
        formatted_incidents = []

        for incident in yaml_incidents:
            if platform == "pagerduty":
                # PagerDuty incident format
                formatted_incident = {
                    "id": incident['id'],
                    "title": incident['title'],
                    "created_at": incident['created_at'],
                    "resolved_at": incident.get('resolved_at'),
                    "status": incident.get('status', 'resolved'),
                    "severity": incident.get('severity', 'medium'),
                    "assigned_to": {
                        "id": incident['assigned_user_id'],
                        "name": incident.get('assigned_user_name', ''),
                        "email": incident.get('assigned_user_email', '')
                    }
                }
            else:
                # Rootly incident format (JSON:API structure)
                formatted_incident = {
                    "id": incident['id'],
                    "type": "incidents",
                    "attributes": {
                        "title": incident['title'],
                        "started_at": incident['created_at'],
                        "resolved_at": incident.get('resolved_at'),
                        "severity": incident.get('severity', 'medium'),
                        "status": incident.get('status', 'resolved'),
                        "user": {
                            "data": {
                                "id": incident['assigned_user_id'],
                                "name": incident.get('assigned_user_name', ''),
                                "email": incident.get('assigned_user_email', '')
                            }
                        }
                    }
                }

            formatted_incidents.append(formatted_incident)

        return formatted_incidents

    def get_github_data(self, scenario_name: str) -> Dict[str, Any]:
        """
        Get GitHub-formatted data for a scenario
        Matches the structure from github_raw.txt

        Args:
            scenario_name: Name of the scenario to load

        Returns:
            Dictionary with email as key, GitHub data as value
        """
        scenario_data = self.load_scenario(scenario_name)

        github_data = {}
        for user in scenario_data['users']:
            email = user['email']
            github_info = user.get('github', {})

            # Calculate analysis period (30 days back from now)
            end_time = datetime.now()
            start_time = datetime.now().replace(day=end_time.day - 30) if end_time.day > 30 else datetime.now().replace(month=end_time.month - 1)

            github_data[email] = {
                "username": user['username'],
                "email": email,
                "analysis_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": 30
                },
                "metrics": {
                    "total_commits": github_info.get('total_commits', 0),
                    "total_pull_requests": github_info.get('total_pull_requests', 0),
                    "total_reviews": github_info.get('total_reviews', 0),
                    "commits_per_week": github_info.get('commits_per_week', 0.0),
                    "prs_per_week": github_info.get('prs_per_week', 0.0),
                    "after_hours_commit_percentage": github_info.get('after_hours_commit_percentage', 0.0),
                    "weekend_commit_percentage": github_info.get('weekend_commit_percentage', 0.0),
                    "repositories_touched": github_info.get('repositories_touched', 0),
                    "avg_pr_size": github_info.get('avg_pr_size', 0),
                    "clustered_commits": github_info.get('clustered_commits', 0)
                },
                "burnout_indicators": github_info.get('burnout_indicators', {}),
                "activity_data": github_info.get('activity_data', {})
            }

        return github_data

    def get_slack_data(self, scenario_name: str) -> Dict[str, Any]:
        """
        Get Slack-formatted data for a scenario
        Matches the structure from slack_raw.txt

        Args:
            scenario_name: Name of the scenario to load

        Returns:
            Dictionary with user name as key, Slack data as value
        """
        scenario_data = self.load_scenario(scenario_name)

        slack_data = {}
        for user in scenario_data['users']:
            user_name = user['name']
            slack_info = user.get('slack', {})

            # Calculate analysis period
            end_time = datetime.now()
            start_time = datetime.now().replace(day=end_time.day - 30) if end_time.day > 30 else datetime.now().replace(month=end_time.month - 1)

            slack_data[user_name] = {
                "user_id": user_name,
                "email": user['email'],
                "analysis_period": {
                    "start": start_time.isoformat(),
                    "end": end_time.isoformat(),
                    "days": 30
                },
                "metrics": {
                    "total_messages": slack_info.get('total_messages', 0),
                    "messages_per_day": slack_info.get('messages_per_day', 0.0),
                    "after_hours_percentage": slack_info.get('after_hours_percentage', 0),
                    "weekend_percentage": slack_info.get('weekend_percentage', 0),
                    "channel_diversity": slack_info.get('channel_diversity', 0),
                    "dm_ratio": slack_info.get('dm_ratio', 0.0),
                    "thread_participation_rate": slack_info.get('thread_participation_rate', 0.0),
                    "avg_message_length": slack_info.get('avg_message_length', 0),
                    "peak_hour_concentration": slack_info.get('peak_hour_concentration', 0.0),
                    "response_pattern_score": slack_info.get('response_pattern_score', 0.0),
                    "avg_sentiment": slack_info.get('avg_sentiment', 0.0),
                    "negative_sentiment_ratio": slack_info.get('negative_sentiment_ratio', 0.0),
                    "positive_sentiment_ratio": slack_info.get('positive_sentiment_ratio', 0.0),
                    "stress_indicator_ratio": slack_info.get('stress_indicator_ratio', 0.0),
                    "sentiment_volatility": slack_info.get('sentiment_volatility', 0.0)
                },
                "burnout_indicators": slack_info.get('burnout_indicators', {}),
                "activity_data": slack_info.get('activity_data', {}),
                "fetch_errors": slack_info.get('fetch_errors', {"rate_limited_channels": [], "errors": []})
            }

        return slack_data

    def get_scenario_info(self, scenario_name: str) -> Dict[str, str]:
        """
        Get metadata about a scenario

        Args:
            scenario_name: Name of the scenario

        Returns:
            Dictionary with scenario name and description
        """
        scenario_data = self.load_scenario(scenario_name)
        return {
            "name": scenario_data.get('scenario_name', scenario_name),
            "description": scenario_data.get('description', '')
        }


# Convenience function for quick testing
def load_mock_scenario(scenario_name: str = "healthy_team", platform: str = "rootly") -> Dict[str, Any]:
    """
    Quick function to load a mock scenario

    Args:
        scenario_name: Name of scenario (healthy_team, high_burnout, mixed_burnout)
        platform: "rootly" or "pagerduty"

    Returns:
        Formatted data ready for UnifiedBurnoutAnalyzer

    Example:
        >>> data = load_mock_scenario("high_burnout")
        >>> analyzer = UnifiedBurnoutAnalyzer(...)
        >>> # Use data instead of API calls
    """
    loader = MockDataLoader()
    return loader.get_unified_data(scenario_name, platform)
