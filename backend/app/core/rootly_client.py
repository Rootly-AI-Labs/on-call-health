"""
Rootly API client for direct HTTP integration.

Timeout and retry settings based on API benchmark (2026-01-20):
- incidents endpoints: avg 10-15s, p95 15-21s, max 21s
- users/schedules: avg <1s, p95 <2s

Recommended settings:
- Default timeout: 30s (covers most endpoints)
- Incidents timeout: 32s (1.5x P99 latency)
- Retries: 3 with exponential backoff [2s, 4s, 8s]
"""
import asyncio
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from urllib.parse import urlencode

from .config import settings

logger = logging.getLogger(__name__)

# Timeout settings based on API benchmark
DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=10.0)
INCIDENTS_TIMEOUT = httpx.Timeout(32.0, connect=10.0)  # Incidents are slow (p95=21s)

# Retry settings
MAX_RETRIES = 3
RETRY_DELAYS = [2, 4, 8]  # Exponential backoff delays in seconds

# Retryable exceptions for network errors
RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadError,
    httpx.WriteError,
    httpx.ConnectTimeout,
    httpx.ReadTimeout,
    ConnectionResetError,
    ConnectionError,
    OSError,
)


class RootlyAPIClient:
    """Direct HTTP client for Rootly API."""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = settings.ROOTLY_API_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/vnd.api+json",
            "Accept": "application/vnd.api+json"
        }

    async def _request_with_retry(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        max_retries: int = MAX_RETRIES,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with retry logic for transient network errors.

        Uses exponential backoff with delays defined in RETRY_DELAYS.

        Args:
            client: The httpx AsyncClient to use
            method: HTTP method (GET, POST, etc.)
            url: The URL to request
            max_retries: Maximum number of retry attempts (default: MAX_RETRIES)
            **kwargs: Additional arguments to pass to the request

        Returns:
            httpx.Response object

        Raises:
            The last exception if all retries fail
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                if method.upper() == "GET":
                    response = await client.get(url, **kwargs)
                elif method.upper() == "POST":
                    response = await client.post(url, **kwargs)
                else:
                    response = await client.request(method, url, **kwargs)
                return response

            except RETRYABLE_EXCEPTIONS as e:
                last_exception = e
                if attempt < max_retries:
                    # Use predefined exponential backoff delays
                    delay = RETRY_DELAYS[attempt] if attempt < len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                    logger.warning(
                        f"Rootly API request failed (attempt {attempt + 1}/{max_retries + 1}): "
                        f"{type(e).__name__}: {e}. Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Rootly API request failed after {max_retries + 1} attempts: "
                        f"{type(e).__name__}: {e}"
                    )
                    raise
            except Exception as e:
                # Non-retryable exception, raise immediately
                logger.error(f"Rootly API request failed with non-retryable error: {type(e).__name__}: {e}")
                raise

        # This should not be reached, but just in case
        if last_exception:
            raise last_exception

    async def check_permissions(self) -> Dict[str, Any]:
        """Check permissions for specific API endpoints."""
        permissions = {
            "users": {"access": False, "error": None},
            "incidents": {"access": False, "error": None}
        }
        
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                # Test users endpoint
                try:
                    response = await client.get(
                        f"{self.base_url}/v1/users",
                        headers=self.headers,
                        params={"page[size]": 1}
                    )
                    
                    if response.status_code == 200:
                        permissions["users"]["access"] = True
                        logger.info(f" Rootly users permission check: SUCCESS")
                    elif response.status_code == 401:
                        permissions["users"]["error"] = "Unauthorized - check API token"
                        logger.warning(f"Rootly users permission check: 401 Unauthorized")
                    elif response.status_code == 403:
                        permissions["users"]["error"] = "Token needs 'users:read' permission"
                        logger.warning(f"Rootly users permission check: 403 Forbidden")
                    elif response.status_code == 404:
                        permissions["users"]["error"] = "API token doesn't have access to user data"
                        logger.warning(f"Rootly users permission check: 404 Not Found")
                    else:
                        permissions["users"]["error"] = f"HTTP {response.status_code}"
                        logger.warning(f"Rootly users permission check: HTTP {response.status_code}")

                except Exception as e:
                    permissions["users"]["error"] = f"Connection error: {str(e)}"
                    logger.error(f"Rootly users permission check: Exception - {str(e)}")
                
                # Test incidents endpoint
                try:
                    response = await client.get(
                        f"{self.base_url}/v1/incidents",
                        headers=self.headers,
                        params={"page[size]": 1},
                        timeout=30.0  # Increased from 10s to match other API calls
                    )
                    
                    if response.status_code == 200:
                        permissions["incidents"]["access"] = True
                    elif response.status_code == 401:
                        permissions["incidents"]["error"] = "Unauthorized - check API token"
                    elif response.status_code == 403:
                        permissions["incidents"]["error"] = "Token needs 'incidents:read' permission"
                    elif response.status_code == 404:
                        permissions["incidents"]["error"] = "API token doesn't have access to incident data"
                    else:
                        permissions["incidents"]["error"] = f"HTTP {response.status_code}"
                        
                except Exception as e:
                    permissions["incidents"]["error"] = f"Connection error: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error checking permissions: {e}")
            permissions["users"]["error"] = f"General error: {str(e)}"
            permissions["incidents"]["error"] = f"General error: {str(e)}"
            
        return permissions

    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection and return basic account info with permissions."""
        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                # Make both API calls in parallel for faster response
                me_task = client.get(
                    f"{self.base_url}/v1/users/me",
                    headers=self.headers
                )
                users_task = client.get(
                    f"{self.base_url}/v1/users?page[size]=1",
                    headers=self.headers
                )

                # Wait for both calls to complete in parallel
                me_response, users_response = await asyncio.gather(me_task, users_task)

                # Check /v1/users/me response for errors
                if me_response.status_code != 200:
                    if me_response.status_code == 401:
                        return {
                            "status": "error",
                            "message": "Invalid API token",
                            "error_code": "UNAUTHORIZED"
                        }
                    elif me_response.status_code == 404:
                        return {
                            "status": "error",
                            "message": "API endpoint not found - check your Rootly configuration",
                            "error_code": "NOT_FOUND"
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"API request failed with status {me_response.status_code}",
                            "error_code": "API_ERROR"
                        }

                me_data = me_response.json()
                if me_data is None:
                    logger.error("API response json() returned None")
                    return {
                        "status": "error",
                        "message": "Invalid JSON response from API",
                        "error_code": "INVALID_RESPONSE"
                    }

                # Extract organization name from authenticated user
                organization_name = None
                if "data" in me_data and isinstance(me_data["data"], dict):
                    user = me_data["data"]
                    if "attributes" in user:
                        attrs = user["attributes"]
                        logger.info(f" Rootly API returned user attributes: full_name_with_team='{attrs.get('full_name_with_team')}', organization_name='{attrs.get('organization_name')}', company='{attrs.get('company')}'")

                        # Extract organization name from full_name_with_team: "[Team Name] User Name"
                        if "full_name_with_team" in attrs:
                            full_name_with_team = attrs["full_name_with_team"]
                            if full_name_with_team and full_name_with_team.startswith("[") and "]" in full_name_with_team:
                                organization_name = full_name_with_team.split("]")[0][1:]
                                logger.info(f" Extracted org name from full_name_with_team: '{organization_name}'")
                        # Fallback to other fields
                        elif "organization_name" in attrs:
                            organization_name = attrs["organization_name"]
                            logger.info(f" Using organization_name attribute: '{organization_name}'")
                        elif "company" in attrs:
                            organization_name = attrs["company"]
                            logger.info(f" Using company attribute: '{organization_name}'")

                # Extract total user count from /v1/users response
                total_users = 0
                if users_response.status_code == 200:
                    users_data = users_response.json()
                    if users_data and "meta" in users_data:
                        total_users = users_data["meta"].get("total_count", 0)
                        logger.debug(f"Rootly users API: {total_users} total users")

                # Build account info
                account_info = {
                    "api_version": "v1",
                    "total_users": total_users
                }

                if organization_name:
                    account_info["organization_name"] = organization_name

                # Check permissions for required endpoints (run in parallel with main requests if needed)
                permissions = await self.check_permissions()
                account_info["permissions"] = permissions

                return {
                    "status": "success",
                    "message": "Connected successfully",
                    "account_info": account_info
                }
                    
        except httpx.ConnectError:
            return {
                "status": "error",
                "message": "Unable to connect to Rootly API - check your internet connection",
                "error_code": "CONNECTION_ERROR"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Unexpected error: {str(e)}",
                "error_code": "UNKNOWN_ERROR"
            }
    
    async def get_users(self, limit: int = 100, include_role: bool = False):
        """Fetch users from Rootly API.

        Args:
            limit: Maximum number of users to fetch
            include_role: If True, includes role relationship to identify incident responders

        Returns:
            If include_role is True: Tuple of (users, included_data)
            Otherwise: List of users
        """
        all_users = []
        all_included = []
        page = 1
        page_size = min(limit, 100)  # Rootly API typically limits to 100 per page

        try:
            async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
                while len(all_users) < limit:
                    # URL encode the parameters manually since httpx doesn't encode brackets properly
                    params = {
                        "page[number]": page,
                        "page[size]": page_size
                    }

                    # Add include parameter if requested
                    if include_role:
                        params["include"] = "role"

                    params_encoded = urlencode(params)

                    response = await client.get(
                        f"{self.base_url}/v1/users?{params_encoded}",
                        headers=self.headers
                    )

                    if response.status_code != 200:
                        logger.error(f"Rootly API request failed: {response.status_code}")
                        raise Exception(f"API request failed: {response.status_code}")

                    data = response.json()

                    # Safety check for data
                    if data is None:
                        logger.error("Users API response returned None")
                        break

                    users = data.get("data", [])

                    if not users:
                        break

                    all_users.extend(users)

                    # Collect included data if present (for role details)
                    if include_role:
                        included = data.get("included", [])
                        all_included.extend(included)

                    # Check if we have more pages
                    meta = data.get("meta", {})
                    total_pages = meta.get("total_pages", 1)

                    if page >= total_pages:
                        break

                    page += 1

                # Return users and included data if role was requested
                if include_role:
                    return all_users[:limit], all_included
                else:
                    return all_users[:limit]

        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            raise
    
    async def get_on_call_shifts(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Get on-call shifts for a specific time period from Rootly.

        Rootly API structure:
        1. First get all schedules via /v1/schedules
        2. For each schedule, get shifts via /v1/schedules/{id}/shifts with date filters

        Uses parallel fetching with asyncio.gather() for performance.
        """
        try:
            # Format dates for API (Rootly expects ISO format)
            start_str = start_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            end_str = end_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ')

            all_shifts = []

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Get all schedules (with retry)
                schedules_response = await self._request_with_retry(
                    client,
                    "GET",
                    f"{self.base_url}/v1/schedules",
                    headers=self.headers,
                    params={"page[size]": 100},
                    timeout=30.0
                )

                if schedules_response.status_code != 200:
                    logger.error(f"Failed to fetch on-call schedules: {schedules_response.status_code}")
                    return []

                schedules_data = schedules_response.json()
                schedules = schedules_data.get('data', [])
                logger.info(f"Fetching shifts for {len(schedules)} schedules in parallel...")

                # Step 2: Fetch shifts for ALL schedules in parallel
                async def fetch_schedule_shifts(schedule):
                    schedule_id = schedule.get('id')
                    schedule_name = schedule.get('attributes', {}).get('name', 'Unknown')
                    try:
                        shifts_response = await self._request_with_retry(
                            client,
                            "GET",
                            f"{self.base_url}/v1/schedules/{schedule_id}/shifts",
                            headers=self.headers,
                            params={
                                'filter[starts_at][lt]': end_str,
                                'filter[ends_at][gt]': start_str,
                                'include': 'user',
                                'page[size]': 100
                            },
                            timeout=30.0
                        )

                        if shifts_response.status_code == 200:
                            shifts_data = shifts_response.json()
                            return shifts_data.get('data', [])
                        else:
                            logger.warning(f"Failed to fetch shifts for schedule {schedule_name}: {shifts_response.status_code}")
                            return []

                    except RETRYABLE_EXCEPTIONS as e:
                        logger.error(f"Failed to fetch shifts for schedule {schedule_name} after retries: {e}")
                        return []

                # Run all schedule fetches in parallel
                results = await asyncio.gather(*[fetch_schedule_shifts(s) for s in schedules], return_exceptions=True)

                # Collect results, handling any exceptions
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        schedule_name = schedules[i].get('attributes', {}).get('name', 'Unknown')
                        logger.error(f"Exception fetching shifts for schedule {schedule_name}: {result}")
                    elif result:
                        all_shifts.extend(result)

                logger.info(f"Found {len(all_shifts)} shifts across {len(schedules)} schedules")
                return all_shifts

        except Exception as e:
            logger.error(f"Error fetching on-call shifts: {e}")
            return []
    
    async def extract_on_call_users_from_shifts(self, shifts: List[Dict[str, Any]]) -> set:
        """
        Extract unique user emails from shifts data.
        Returns set of user emails who were on-call during the period.
        """
        if not shifts or shifts is None:
            return set()

        # Step 1: Extract unique user IDs from shifts
        user_ids = set()
        for shift in shifts:
            try:
                if not shift or not isinstance(shift, dict):
                    continue

                relationships = shift.get('relationships', {})
                if not relationships:
                    continue

                user_data = relationships.get('user', {}).get('data', {})

                if user_data and user_data.get('type') == 'users':
                    user_id = user_data.get('id')
                    if user_id:
                        user_ids.add(user_id)

            except Exception as e:
                logger.warning(f"Error extracting user from shift: {e}")
                continue
        
        # Step 2: Fetch user details to get emails (in parallel)
        on_call_user_emails = set()

        if user_ids:
            try:
                logger.info(f"Fetching {len(user_ids)} user details in parallel...")

                async with httpx.AsyncClient(timeout=15.0) as client:
                    async def fetch_user_email(user_id):
                        try:
                            response = await client.get(
                                f"{self.base_url}/v1/users/{user_id}",
                                headers=self.headers
                            )

                            if response.status_code == 200:
                                user_data = response.json()
                                if 'data' in user_data:
                                    attributes = user_data['data'].get('attributes', {})
                                    email = attributes.get('email')
                                    if email:
                                        return email.lower().strip()
                            return None

                        except Exception as e:
                            logger.warning(f"Error fetching user {user_id}: {e}")
                            return None

                    # Fetch all users in parallel
                    results = await asyncio.gather(*[fetch_user_email(uid) for uid in user_ids], return_exceptions=True)

                    # Collect valid emails
                    for result in results:
                        if isinstance(result, str):
                            on_call_user_emails.add(result)
                        elif isinstance(result, Exception):
                            logger.warning(f"Exception fetching user: {result}")

                logger.info(f"Found {len(on_call_user_emails)} on-call user emails")

            except Exception as e:
                logger.error(f"Error fetching on-call user details: {e}")

        return on_call_user_emails

    def filter_incident_responders(self, users: List[Dict[str, Any]], included_data: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Filter users to only those who are incident responders (have IR role).

        Filters OUT observers and users without IR access.
        Includes: admin, owner, user, and custom roles.

        Args:
            users: List of user objects from Rootly API (must include role relationship)
            included_data: Optional included section from API response with full role details

        Returns:
            Filtered list of users who are incident responders
        """
        # Build a map of role_id -> role details from included data
        role_map = {}
        if included_data:
            for item in included_data:
                if item.get('type') == 'roles':
                    role_id = item.get('id')
                    slug = item.get('attributes', {}).get('slug')
                    name = item.get('attributes', {}).get('name')
                    role_map[role_id] = {
                        'slug': slug,
                        'name': name
                    }

        incident_responders = []

        for user in users:
            try:
                email = user.get('attributes', {}).get('email', 'unknown')

                # Check if user has role relationship (IR role)
                relationships = user.get('relationships', {})
                role = relationships.get('role', {})
                role_data = role.get('data')

                # No role = not an incident responder
                if not role_data:
                    logger.debug(f"User {email} has no IR role")
                    continue

                role_id = role_data.get('id')

                # If we have role details, check the slug
                if role_id and role_id in role_map:
                    slug = role_map[role_id]['slug']
                    role_name = role_map[role_id]['name']

                    # Exclude observers and no_access (they're not incident responders)
                    if slug in ['observer', 'no_access']:
                        logger.debug(f"User {email} has {role_name} role (not incident responder)")
                        continue

                    # Include admin, owner, user, and custom roles
                    incident_responders.append(user)
                    logger.debug(f"User {email} is incident responder (role: {role_name})")
                else:
                    # If we don't have role details, include them (fail-safe)
                    incident_responders.append(user)
                    logger.debug(f"User {email} has IR role (no role details available)")

            except Exception as e:
                logger.warning(f"Error checking IR role for user: {e}")
                continue

        logger.info(f" Filtered {len(users)} users → {len(incident_responders)} incident responders (excluded observers/no_access)")
        return incident_responders

    async def get_incidents(self, days_back: int = 30, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch incidents from Rootly API.

        Uses INCIDENTS_TIMEOUT (32s) based on benchmark showing incidents
        endpoints have avg 10-15s latency with p95 up to 21s.
        """
        fetch_start_time = datetime.now()
        all_incidents = []
        page = 1
        page_size = min(100, limit)  # Rootly API page size limit
        api_calls_made = 0

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        try:
            async with httpx.AsyncClient(timeout=INCIDENTS_TIMEOUT) as client:
                # Test basic access to incidents endpoint
                test_response = await client.get(
                    f"{self.base_url}/v1/incidents",
                    headers=self.headers,
                    params={"page[size]": 1}
                )
                api_calls_made += 1

                if test_response.status_code == 404:
                    logger.error("Cannot access incidents endpoint - check API token permissions")
                    raise Exception("Cannot access incidents endpoint. Please verify your Rootly API token has 'incidents:read' permission.")
                elif test_response.status_code != 200:
                    logger.error(f"Incidents endpoint failed: {test_response.status_code}")
                    raise Exception(f"Basic incidents endpoint failed: {test_response.status_code}")
                
                pagination_start = datetime.now()
                consecutive_failures = 0
                max_consecutive_failures = 3
                total_pagination_timeout = 600  # 10 minutes max for all pagination
                
                while len(all_incidents) < limit and consecutive_failures < max_consecutive_failures:
                    page_start_time = datetime.now()

                    # Use adaptive page size based on time range
                    if days_back >= 90:
                        actual_page_size = min(page_size, 100)
                    elif days_back >= 30:
                        actual_page_size = min(page_size, 50)
                    else:
                        actual_page_size = min(page_size, 20)

                    params = {
                        "page[number]": page,
                        "page[size]": actual_page_size,
                        "filter[created_at][gte]": start_date.isoformat(),
                        "filter[created_at][lte]": end_date.isoformat(),
                        "include": "severity,user,started_by,resolved_by",
                        "fields[incidents]": "created_at,started_at,acknowledged_at,resolved_at,mitigated_at,severity,user,title,status"
                    }

                    params_encoded = urlencode(params)

                    try:
                        # Check if we've exceeded total pagination timeout
                        pagination_elapsed = (datetime.now() - pagination_start).total_seconds()
                        if pagination_elapsed > total_pagination_timeout:
                            logger.error(f"🕐 PAGINATION TIMEOUT: Exceeded {total_pagination_timeout}s limit after {len(all_incidents)} incidents")
                            logger.error(f"🕐 PAGINATION TIMEOUT: Started at {pagination_start}, elapsed {pagination_elapsed:.2f}s")
                            break

                        response = await client.get(
                            f"{self.base_url}/v1/incidents?{params_encoded}",
                            headers=self.headers
                        )
                        api_calls_made += 1
                    except (asyncio.TimeoutError, httpx.TimeoutException):
                        # Explicit timeout exception handling
                        logger.error(f"🕐 API REQUEST TIMEOUT: Rootly incidents request timed out")
                        logger.error(f"🕐 API REQUEST TIMEOUT: Page {page}, collected {len(all_incidents)} incidents so far")
                        consecutive_failures += 1

                        if consecutive_failures >= max_consecutive_failures:
                            if all_incidents:
                                logger.warning(f"Stopping after {consecutive_failures} timeout failures. Returning {len(all_incidents)} incidents.")
                                break
                            else:
                                raise
                        else:
                            # Use predefined retry delays
                            delay = RETRY_DELAYS[consecutive_failures - 1] if consecutive_failures <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                            await asyncio.sleep(delay)
                            continue
                    except Exception as request_error:
                        consecutive_failures += 1
                        logger.error(f"Incident request failed: {request_error} (failure {consecutive_failures}/{max_consecutive_failures})")

                        # If we have some incidents already, continue with partial data
                        if consecutive_failures >= max_consecutive_failures:
                            if all_incidents:
                                logger.warning(f"Stopping after {consecutive_failures} consecutive failures. Returning {len(all_incidents)} incidents.")
                                break
                            else:
                                raise request_error
                        else:
                            # Use predefined retry delays
                            delay = RETRY_DELAYS[consecutive_failures - 1] if consecutive_failures <= len(RETRY_DELAYS) else RETRY_DELAYS[-1]
                            await asyncio.sleep(delay)
                            continue

                    if response.status_code != 200:
                        consecutive_failures += 1
                        error_detail = response.text
                        logger.error(f"API error: {response.status_code} (failure {consecutive_failures}/{max_consecutive_failures})")

                        # Handle specific error cases
                        if response.status_code == 404 and "not found or unauthorized" in error_detail.lower():
                            raise Exception(f"Rootly API access denied. Check API token has 'incidents:read' permission.")
                        elif response.status_code in [429, 502, 503, 504]:
                            if consecutive_failures >= max_consecutive_failures:
                                if all_incidents:
                                    logger.warning(f"API errors after {consecutive_failures} attempts. Returning {len(all_incidents)} incidents.")
                                    break
                                else:
                                    raise Exception(f"API repeatedly failing: {response.status_code}")
                            else:
                                # Use longer delays for server errors/rate limits
                                delay = RETRY_DELAYS[consecutive_failures - 1] * 2 if consecutive_failures <= len(RETRY_DELAYS) else RETRY_DELAYS[-1] * 2
                                await asyncio.sleep(delay)
                                continue
                        else:
                            raise Exception(f"API request failed: {response.status_code}")
                    else:
                        consecutive_failures = 0

                    data = response.json()

                    if data is None:
                        logger.error("API response returned None")
                        break

                    incidents = data.get("data", [])

                    if not incidents:
                        break

                    # DEBUG: Log first incident to see severity structure
                    if len(all_incidents) == 0 and len(incidents) > 0:
                        first_incident = incidents[0]
                        severity_data = first_incident.get("attributes", {}).get("severity")
                        logger.info(f"🔍 FIRST INCIDENT SEVERITY CHECK:")
                        logger.info(f"  - Incident ID: {first_incident.get('id')}")
                        logger.info(f"  - Severity type: {type(severity_data)}")
                        logger.info(f"  - Severity value: {severity_data}")
                        if isinstance(severity_data, dict):
                            logger.info(f"  - Has 'data' key: {'data' in severity_data}")

                    all_incidents.extend(incidents)

                    # Check if we have more pages
                    meta = data.get("meta", {})
                    total_pages = meta.get("total_pages", 1)

                    if page >= total_pages:
                        break

                    page += 1

                total_fetch_duration = (datetime.now() - fetch_start_time).total_seconds()

                if days_back >= 30 and total_fetch_duration > 600:
                    logger.warning(f"Incident fetch took {total_fetch_duration:.2f}s - may cause timeout")

                return all_incidents[:limit]

        except Exception as e:
            logger.error(f"Incident fetch failed: {e}")
            raise
    
    async def get_user_incident_roles(self, user_id: str, incident_ids: List[str]) -> List[Dict[str, Any]]:
        """Get user roles for specific incidents."""
        # This would require additional API calls to incident role endpoints
        # For now, return empty list - this can be expanded based on Rootly API capabilities
        return []
    
    async def collect_analysis_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Collect all data needed for burnout analysis."""
        start_time = datetime.now()

        try:
            # Test connection first
            connection_test = await self.test_connection()

            if connection_test["status"] != "success":
                raise Exception(f"Connection test failed: {connection_test['message']}")

            # Collect users and incidents in parallel (no limits for complete data collection)
            users_task = self.get_users(limit=10000)  # Get all users (increased from 1000)

            # Use conservative incident limits to prevent timeout on longer analyses
            incident_limits_by_range = {
                7: 1500,
                14: 2000,
                30: 3000,
                60: 4000,
                90: 5000,
                180: 7500
            }

            incident_limit = 5000
            for range_days in sorted(incident_limits_by_range.keys()):
                if days_back <= range_days:
                    incident_limit = incident_limits_by_range[range_days]
                    break

            incidents_task = self.get_incidents(days_back=days_back, limit=incident_limit)

            # Collect users (required)
            users = await users_task

            # Try to collect incidents but don't fail if permission denied
            incidents = []
            try:
                incidents = await incidents_task
            except Exception as e:
                logger.warning(f"Could not fetch incidents: {e}. Proceeding with user data only.")

            # Validate data
            if not users:
                raise Exception("No users found - check API permissions")
            
            # Calculate severity breakdown using shared utility
            from app.utils.incident_utils import calculate_severity_breakdown
            severity_counts = calculate_severity_breakdown(incidents)
            
            # Process and return data
            processed_data = {
                "users": users,
                "incidents": incidents,
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_back,
                    "total_users": len(users),
                    "total_incidents": len(incidents),
                    "severity_breakdown": severity_counts,
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "end": datetime.now().isoformat()
                    },
                }
            }

            return processed_data

        except Exception as e:
            logger.error(f"Data collection failed: {e}")
            # Return minimal data structure instead of failing completely
            return {
                "users": [],
                "incidents": [],
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_back,
                    "total_users": 0,
                    "total_incidents": 0,
                    "severity_breakdown": {
                        "sev0_count": 0,
                        "sev1_count": 0,
                        "sev2_count": 0,
                        "sev3_count": 0,
                        "sev4_count": 0
                    },
                    "error": str(e),
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "end": datetime.now().isoformat()
                    },
                    "performance_metrics": {
                        "total_collection_time_seconds": total_duration,
                        "failed": True
                    }
                }
            }