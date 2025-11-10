"""Grafana API client - independent HTTP client module."""

import requests
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GrafanaAPIError(Exception):
    """Grafana API error."""
    pass


class GrafanaClient:
    """
    Independent Grafana API client.

    This module only handles HTTP communication with Grafana.
    It doesn't know about application-specific data models.
    """

    def __init__(
        self,
        url: str,
        token: str,
        verify_ssl: bool = True,
        timeout: int = 30
    ):
        """
        Initialize Grafana client.

        Args:
            url: Grafana base URL (e.g., https://grafana.example.com)
            token: API token for authentication
            verify_ssl: Whether to verify SSL certificates
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip('/')
        self.token = token
        self.verify_ssl = verify_ssl
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request to Grafana API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/api/health')
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            GrafanaAPIError: If request fails
        """
        url = f"{self.url}{endpoint}"

        kwargs.setdefault('verify', self.verify_ssl)
        kwargs.setdefault('timeout', self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Grafana API request failed: {e}")
            raise GrafanaAPIError(f"API request failed: {e}") from e

    def test_connection(self) -> bool:
        """
        Test connection to Grafana API.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = self._request('GET', '/api/health')
            return response.status_code == 200
        except GrafanaAPIError:
            return False

    def get_datasources(self) -> List[Dict[str, Any]]:
        """
        Get list of available datasources.

        Returns:
            List of datasource objects
        """
        try:
            response = self._request('GET', '/api/datasources')
            return response.json()
        except GrafanaAPIError:
            logger.warning("Failed to get datasources")
            return []

    def get_datasource_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """
        Get datasource by UID.

        Args:
            uid: Datasource UID

        Returns:
            Datasource object or None
        """
        try:
            response = self._request('GET', f'/api/datasources/uid/{uid}')
            return response.json()
        except GrafanaAPIError:
            return None

    def query_prometheus(
        self,
        datasource_uid: str,
        query: str,
        start: datetime,
        end: datetime,
        step: int = 60
    ) -> Dict[str, Any]:
        """
        Query Prometheus datasource.

        Args:
            datasource_uid: Datasource UID
            query: PromQL query
            start: Start time
            end: End time
            step: Step in seconds

        Returns:
            Query result
        """
        payload = {
            'queries': [{
                'datasource': {'type': 'prometheus', 'uid': datasource_uid},
                'expr': query,
                'refId': 'A',
                'instant': False,
                'range': True,
                'format': 'time_series'
            }],
            'from': str(int(start.timestamp() * 1000)),
            'to': str(int(end.timestamp() * 1000))
        }

        try:
            response = self._request('POST', '/api/ds/query', json=payload)
            return response.json()
        except GrafanaAPIError as e:
            logger.error(f"Prometheus query failed: {e}")
            return {}

    def get_dashboard(self, dashboard_uid: str) -> Dict[str, Any]:
        """
        Get dashboard by UID.

        Args:
            dashboard_uid: Dashboard UID

        Returns:
            Dashboard object
        """
        try:
            response = self._request('GET', f'/api/dashboards/uid/{dashboard_uid}')
            return response.json()
        except GrafanaAPIError:
            return {}

    def search_dashboards(
        self,
        query: str = "",
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for dashboards.

        Args:
            query: Search query
            tags: Filter by tags

        Returns:
            List of dashboard objects
        """
        params = {'query': query, 'type': 'dash-db'}
        if tags:
            params['tag'] = tags

        try:
            response = self._request('GET', '/api/search', params=params)
            return response.json()
        except GrafanaAPIError:
            return []

    def get_annotations(
        self,
        start: datetime,
        end: datetime,
        tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get annotations for a time range.

        Args:
            start: Start time
            end: End time
            tags: Filter by tags

        Returns:
            List of annotations
        """
        params = {
            'from': int(start.timestamp() * 1000),
            'to': int(end.timestamp() * 1000)
        }
        if tags:
            params['tags'] = tags

        try:
            response = self._request('GET', '/api/annotations', params=params)
            return response.json()
        except GrafanaAPIError:
            return []

    def health_check(self) -> Dict[str, Any]:
        """
        Get Grafana health status.

        Returns:
            Health status info
        """
        try:
            response = self._request('GET', '/api/health')
            return response.json()
        except GrafanaAPIError:
            return {'status': 'error'}
