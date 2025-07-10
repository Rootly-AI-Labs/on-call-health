"""
Rootly API client for direct HTTP integration.
"""
import httpx
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from urllib.parse import urlencode

from .config import settings

logger = logging.getLogger(__name__)

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
    
    async def check_permissions(self) -> Dict[str, Any]:
        """Check permissions for specific API endpoints."""
        permissions = {
            "users": {"access": False, "error": None},
            "incidents": {"access": False, "error": None}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Test users endpoint
                try:
                    response = await client.get(
                        f"{self.base_url}/v1/users",
                        headers=self.headers,
                        params={"page[size]": 1},
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        permissions["users"]["access"] = True
                    elif response.status_code == 401:
                        permissions["users"]["error"] = "Unauthorized - check API token"
                    elif response.status_code == 403:
                        permissions["users"]["error"] = "Forbidden - insufficient permissions"
                    elif response.status_code == 404:
                        permissions["users"]["error"] = "Endpoint not found"
                    else:
                        permissions["users"]["error"] = f"HTTP {response.status_code}"
                        
                except Exception as e:
                    permissions["users"]["error"] = f"Connection error: {str(e)}"
                
                # Test incidents endpoint
                try:
                    response = await client.get(
                        f"{self.base_url}/v1/incidents",
                        headers=self.headers,
                        params={"page[size]": 1},
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        permissions["incidents"]["access"] = True
                    elif response.status_code == 401:
                        permissions["incidents"]["error"] = "Unauthorized - check API token"
                    elif response.status_code == 403:
                        permissions["incidents"]["error"] = "Forbidden - insufficient permissions"
                    elif response.status_code == 404:
                        permissions["incidents"]["error"] = "Endpoint not found"
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
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v1/users",
                    headers=self.headers,
                    params={"page[size]": 1},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Safety check for data
                    if data is None:
                        logger.error("API response json() returned None")
                        return {
                            "status": "error",
                            "message": "Invalid JSON response from API",
                            "error_code": "INVALID_RESPONSE"
                        }
                    
                    # Log full response to examine available organization data
                    print(f"DEBUG: Full Rootly API response: {data}")
                    
                    # Extract any organization/account info from the response
                    organization_name = None
                    account_info = {
                        "total_users": data.get("meta", {}).get("total_count", 0),
                        "api_version": "v1"
                    }
                    
                    # Check if there's organization info in meta or data
                    if "meta" in data:
                        meta = data["meta"]
                        if "organization" in meta:
                            organization_name = meta.get("organization", {}).get("name")
                        elif "account" in meta:
                            organization_name = meta.get("account", {}).get("name")
                    
                    # Check first user data for organization info
                    if "data" in data and data["data"] and len(data["data"]) > 0:
                        first_user = data["data"][0]
                        if "attributes" in first_user:
                            attrs = first_user["attributes"]
                            # Extract organization name from full_name_with_team: "[Team Name] User Name"
                            if "full_name_with_team" in attrs:
                                full_name_with_team = attrs["full_name_with_team"]
                                if full_name_with_team and full_name_with_team.startswith("[") and "]" in full_name_with_team:
                                    organization_name = full_name_with_team.split("]")[0][1:]  # Extract text between [ ]
                            # Fallback to other fields
                            elif "organization_name" in attrs:
                                organization_name = attrs["organization_name"]
                            elif "company" in attrs:
                                organization_name = attrs["company"]
                    
                    if organization_name:
                        account_info["organization_name"] = organization_name
                    
                    # Check permissions for required endpoints
                    permissions = await self.check_permissions()
                    account_info["permissions"] = permissions
                    
                    return {
                        "status": "success",
                        "message": "Connected successfully",
                        "account_info": account_info
                    }
                elif response.status_code == 401:
                    return {
                        "status": "error",
                        "message": "Invalid API token",
                        "error_code": "UNAUTHORIZED"
                    }
                elif response.status_code == 404:
                    return {
                        "status": "error", 
                        "message": "API endpoint not found - check your Rootly configuration",
                        "error_code": "NOT_FOUND"
                    }
                else:
                    return {
                        "status": "error",
                        "message": f"API request failed with status {response.status_code}",
                        "error_code": "API_ERROR"
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
    
    async def get_users(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch users from Rootly API."""
        all_users = []
        page = 1
        page_size = min(limit, 100)  # Rootly API typically limits to 100 per page
        
        try:
            async with httpx.AsyncClient() as client:
                while len(all_users) < limit:
                    # URL encode the parameters manually since httpx doesn't encode brackets properly
                    params_encoded = urlencode({
                        "page[number]": page,
                        "page[size]": page_size
                    })
                    
                    logger.info(f"Fetching users page {page} (page_size: {page_size})")
                    
                    response = await client.get(
                        f"{self.base_url}/v1/users?{params_encoded}",
                        headers=self.headers,
                        timeout=30.0
                    )
                    
                    if response.status_code != 200:
                        logger.error(f"Rootly API request failed: {response.status_code} {response.text}")
                        logger.error(f"Request URL: {self.base_url}/v1/users")
                        logger.error(f"Request headers: Content-Type: {self.headers.get('Content-Type', 'N/A')}")
                        raise Exception(f"API request failed: {response.status_code} {response.text}")
                    
                    data = response.json()
                    
                    # Safety check for data
                    if data is None:
                        logger.error("Users API response json() returned None")
                        break
                    
                    users = data.get("data", [])
                    
                    if not users:
                        logger.info(f"No more users found on page {page}")
                        break
                    
                    all_users.extend(users)
                    logger.info(f"Fetched {len(users)} users from page {page}, total: {len(all_users)}")
                    
                    # Check if we have more pages
                    meta = data.get("meta", {})
                    total_pages = meta.get("total_pages", 1)
                    logger.info(f"Page {page} of {total_pages}")
                    
                    if page >= total_pages:
                        logger.info(f"Reached last page ({page}/{total_pages})")
                        break
                    
                    page += 1
                
                logger.info(f"Fetched {len(all_users)} users from Rootly")
                return all_users[:limit]
                
        except Exception as e:
            logger.error(f"Error fetching users: {e}")
            raise
    
    async def get_incidents(self, days_back: int = 30, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch incidents from Rootly API."""
        all_incidents = []
        page = 1
        page_size = min(100, limit)  # Rootly API page size limit
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        try:
            async with httpx.AsyncClient() as client:
                # First test basic access to incidents endpoint
                test_response = await client.get(
                    f"{self.base_url}/v1/incidents",
                    headers=self.headers,
                    params={"page[size]": 1},
                    timeout=30.0
                )
                
                logger.info(f"Basic incidents test: {test_response.status_code}")
                if test_response.status_code == 404:
                    logger.error("Basic incidents endpoint test failed - checking permissions")
                    raise Exception("Cannot access incidents endpoint. Please verify your Rootly API token has 'incidents:read' permission.")
                elif test_response.status_code != 200:
                    logger.error(f"Basic incidents endpoint test failed: {test_response.status_code} {test_response.text}")
                    raise Exception(f"Basic incidents endpoint failed: {test_response.status_code}")
                else:
                    logger.info("Basic incidents endpoint test passed!")
                
                while len(all_incidents) < limit:
                    # Use smaller page size to reduce timeout risk
                    actual_page_size = min(page_size, 20)  # Start with smaller pages
                    params = {
                        "page[number]": page,
                        "page[size]": actual_page_size,
                        # Temporarily comment out date filters to test basic access
                        # "filter[created_at][gte]": start_date.isoformat(),
                        # "filter[created_at][lte]": end_date.isoformat(),
                        # "include": "severity,user,started_by,resolved_by"
                    }
                    
                    # URL encode the parameters manually since httpx doesn't encode brackets properly
                    params_encoded = urlencode(params)
                    
                    logger.info(f"Requesting incidents page {page} with params: {params}")
                    logger.info(f"Request URL: {self.base_url}/v1/incidents")
                    logger.info(f"Request headers: {self.headers}")
                    
                    try:
                        response = await client.get(
                            f"{self.base_url}/v1/incidents?{params_encoded}",
                            headers=self.headers,
                            timeout=30.0  # Increase timeout to 30 seconds
                        )
                        logger.info(f"Got response status: {response.status_code}")
                    except Exception as request_error:
                        logger.error(f"Request failed with exception: {request_error}")
                        logger.error(f"Exception type: {type(request_error).__name__}")
                        raise request_error
                    
                    if response.status_code != 200:
                        error_detail = response.text
                        logger.error(f"Rootly API request failed: {response.status_code} {error_detail}")
                        logger.error(f"Request URL: {self.base_url}/v1/incidents")
                        logger.error(f"Request headers: Content-Type: {self.headers.get('Content-Type', 'N/A')}")
                        
                        # Provide more helpful error message for common issues
                        if response.status_code == 404 and "not found or unauthorized" in error_detail.lower():
                            raise Exception(f"Rootly API access denied. Please ensure your API token has 'incidents:read' permission and access to incident data. Error: {response.status_code} {error_detail}")
                        else:
                            raise Exception(f"API request failed: {response.status_code} {error_detail}")
                    
                    data = response.json()
                    
                    # Safety check for data
                    if data is None:
                        logger.error("Incidents API response json() returned None")
                        break
                    
                    incidents = data.get("data", [])
                    
                    if not incidents:
                        break
                    
                    all_incidents.extend(incidents)
                    
                    # Check if we have more pages
                    meta = data.get("meta", {})
                    if page >= meta.get("total_pages", 1):
                        break
                    
                    page += 1
                
                logger.info(f"Fetched {len(all_incidents)} incidents from last {days_back} days")
                return all_incidents[:limit]
                
        except Exception as e:
            logger.error(f"Error fetching incidents: {e}")
            raise
    
    async def get_user_incident_roles(self, user_id: str, incident_ids: List[str]) -> List[Dict[str, Any]]:
        """Get user roles for specific incidents."""
        # This would require additional API calls to incident role endpoints
        # For now, return empty list - this can be expanded based on Rootly API capabilities
        return []
    
    async def collect_analysis_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Collect all data needed for burnout analysis."""
        logger.info(f"Starting Rootly data collection for last {days_back} days...")
        
        try:
            # Test connection first
            connection_test = await self.test_connection()
            if connection_test["status"] != "success":
                raise Exception(f"Connection test failed: {connection_test['message']}")
            
            # Collect users and incidents in parallel (no limits for complete data collection)
            users_task = self.get_users(limit=1000)  # Increased to get all users
            incidents_task = self.get_incidents(days_back=days_back, limit=10000)  # Increased to get all incidents
            
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
            
            # Process and return data
            processed_data = {
                "users": users,
                "incidents": incidents,
                "collection_metadata": {
                    "timestamp": datetime.now().isoformat(),
                    "days_analyzed": days_back,
                    "total_users": len(users),
                    "total_incidents": len(incidents),
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "end": datetime.now().isoformat()
                    }
                }
            }
            
            logger.info(f"Data collection completed: {len(users)} users, {len(incidents)} incidents")
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
                    "error": str(e),
                    "date_range": {
                        "start": (datetime.now() - timedelta(days=days_back)).isoformat(),
                        "end": datetime.now().isoformat()
                    }
                }
            }