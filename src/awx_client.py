"""AWX API client wrapper with authentication and error handling."""

import os
import time
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests


class AWXClientError(Exception):
    """Base exception for AWX client errors."""
    pass


class AWXClient:
    """Client for interacting with AWX API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialise AWX client.

        Args:
            base_url: AWX base URL (e.g., https://awx.example.com)
            username: AWX username
            password: AWX password
            timeout: Request timeout in seconds
        """
        self.base_url = (base_url or os.getenv("AWX_URL", "")).rstrip("/")
        self.username = username or os.getenv("AWX_USERNAME")
        self.password = password or os.getenv("AWX_PASSWORD")
        self.timeout = timeout

        if not all([self.base_url, self.username, self.password]):
            raise AWXClientError(
                "Missing required credentials. Set AWX_URL, AWX_USERNAME, and AWX_PASSWORD environment variables."
            )

        self.api_base = urljoin(self.base_url, "/api/v2/")
        self.session = requests.Session()
        self.session.auth = (self.username, self.password)
        self.session.headers.update({"Content-Type": "application/json"})

    def _request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """
        Make HTTP request to AWX API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (relative to /api/v2/)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            AWXClientError: On request failure
        """
        url = urljoin(self.api_base, endpoint.lstrip("/"))
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 404:
                raise AWXClientError(f"Resource not found: {endpoint}")
            elif status_code == 401:
                raise AWXClientError("Authentication failed - check credentials")
            elif status_code == 403:
                raise AWXClientError("Permission denied - insufficient privileges")
            elif status_code >= 500:
                raise AWXClientError(f"AWX server error: {e.response.text[:200]}")
            else:
                raise AWXClientError(f"HTTP {status_code}: {e.response.text[:200]}")
        except requests.exceptions.ConnectionError:
            raise AWXClientError(f"Cannot connect to AWX at {self.base_url}")
        except requests.exceptions.Timeout:
            raise AWXClientError(f"Request timeout after {self.timeout}s")
        except requests.exceptions.RequestException as e:
            raise AWXClientError(f"Request failed: {str(e)}")

    def get_job(self, job_id: int) -> Dict:
        """
        Get job details.

        Args:
            job_id: Job ID

        Returns:
            Job details dictionary
        """
        response = self._request("GET", f"jobs/{job_id}/")
        return response.json()

    def get_job_stdout(self, job_id: int, format: str = "txt", start_line: int = 0) -> str:
        """
        Get job stdout/logs.

        Args:
            job_id: Job ID
            format: Output format (txt, ansi, json, html)
            start_line: Starting line number (for pagination)

        Returns:
            Job output as string
        """
        params = {"format": format}
        if start_line > 0:
            params["start_line"] = start_line

        response = self._request("GET", f"jobs/{job_id}/stdout/", params=params)
        return response.text

    def list_inventories(self, page: int = 1, page_size: int = 50) -> Dict:
        """
        List available inventories.

        Args:
            page: Page number
            page_size: Results per page

        Returns:
            Paginated inventory list
        """
        params = {"page": page, "page_size": page_size}
        response = self._request("GET", "inventories/", params=params)
        return response.json()

    def get_inventory(self, inventory_id: int) -> Dict:
        """
        Get inventory details.

        Args:
            inventory_id: Inventory ID

        Returns:
            Inventory details dictionary
        """
        response = self._request("GET", f"inventories/{inventory_id}/")
        return response.json()

    def get_inventory_hosts(self, inventory_id: int) -> List[Dict]:
        """
        Get all hosts in an inventory.

        Args:
            inventory_id: Inventory ID

        Returns:
            List of host dictionaries
        """
        all_hosts = []
        page = 1
        page_size = 200

        while True:
            params = {"page": page, "page_size": page_size}
            response = self._request("GET", f"inventories/{inventory_id}/hosts/", params=params)
            data = response.json()
            all_hosts.extend(data["results"])

            if not data.get("next"):
                break
            page += 1

        return all_hosts

    def get_host(self, host_id: int) -> Dict:
        """
        Get host details.

        Args:
            host_id: Host ID

        Returns:
            Host details dictionary
        """
        response = self._request("GET", f"hosts/{host_id}/")
        return response.json()

    def get_host_variables(self, host_id: int) -> Dict:
        """
        Get host variables.

        Args:
            host_id: Host ID

        Returns:
            Host variables dictionary
        """
        response = self._request("GET", f"hosts/{host_id}/variable_data/")
        return response.json()

    def search_job_templates(self, name_filter: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Search job templates.

        Args:
            name_filter: Filter by name (case-insensitive substring match)
            limit: Maximum results to return

        Returns:
            List of job template dictionaries
        """
        params = {"page_size": limit}
        if name_filter:
            params["name__icontains"] = name_filter

        response = self._request("GET", "job_templates/", params=params)
        return response.json()["results"]

    def list_jobs(self, status: Optional[str] = None, limit: int = 20, order_by: str = "-id") -> List[Dict]:
        """
        List recent jobs.

        Args:
            status: Filter by status (successful, failed, running, etc.)
            limit: Maximum results to return
            order_by: Sort field (default: -id for newest first)

        Returns:
            List of job dictionaries
        """
        params = {"page_size": limit, "order_by": order_by}
        if status:
            params["status"] = status

        response = self._request("GET", "jobs/", params=params)
        return response.json()["results"]

    def find_inventory_by_name(self, name: str) -> Optional[Dict]:
        """
        Find inventory by name (exact match).

        Args:
            name: Inventory name

        Returns:
            Inventory dictionary or None if not found
        """
        response = self._request("GET", "inventories/", params={"name": name})
        results = response.json()["results"]
        return results[0] if results else None

    def find_host_by_name(self, name: str) -> Optional[Dict]:
        """
        Find host by name (exact match).

        Args:
            name: Host name

        Returns:
            Host dictionary or None if not found
        """
        response = self._request("GET", "hosts/", params={"name": name})
        results = response.json()["results"]
        return results[0] if results else None
