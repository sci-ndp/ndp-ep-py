"""Service update functionality."""

from typing import Any, Dict

from requests.exceptions import HTTPError

from .client_base import APIClientBase


class APIClientServiceUpdate(APIClientBase):
    """Extension of APIClientBase with service update methods."""

    def update_service(
        self, service_id: str, data: Dict[str, Any], server: str = "local"
    ) -> Dict[str, Any]:
        """
        Update an existing service by making a PUT request (full replacement).

        Args:
            service_id: ID of the service to update.
            data: Data for updating the service. Can contain:
                - service_name: Optional unique name of the service
                - service_title: Optional title of the service
                - owner_org: Optional ID of the organization
                - service_url: Optional URL where service is accessible
                - service_type: Optional type (API, Web Service, etc.)
                - notes: Optional additional notes
                - extras: Optional additional metadata
                - health_check_url: Optional health check endpoint
                - documentation_url: Optional documentation URL
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Response JSON data indicating success.

        Raises:
            ValueError: If the update fails.

        Example:
            >>> client.update_service(
            ...     "service-id-123",
            ...     {"service_title": "Updated API", "service_url": "https://..."}
            ... )
            {'message': 'Service updated successfully'}
        """
        url = f"{self.base_url}/services/{service_id}"
        params = {"server": server}
        try:
            response = self.session.put(url, json=data, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)

            if "not found" in error_detail.lower():
                raise ValueError("Error updating service: Not found")
            elif "Reserved key" in error_detail:
                raise ValueError(f"Error updating service: {error_detail}")
            else:
                raise ValueError(f"Error updating service: {error_detail}")

    def patch_service(
        self, service_id: str, data: Dict[str, Any], server: str = "local"
    ) -> Dict[str, Any]:
        """
        Partially update an existing service by making a PATCH request.

        Only updates the fields provided in data, leaving other fields
        unchanged. This is useful when you only want to modify specific
        attributes without affecting the rest of the service.

        Args:
            service_id: ID of the service to update.
            data: Partial data for updating the service. Can contain:
                - service_name: Optional unique name of the service
                - service_title: Optional title of the service
                - owner_org: Optional ID of the organization
                - service_url: Optional URL where service is accessible
                - service_type: Optional type (API, Web Service, etc.)
                - notes: Optional additional notes
                - extras: Optional additional metadata (merged with existing)
                - health_check_url: Optional health check endpoint
                - documentation_url: Optional documentation URL
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Response JSON data indicating success.

        Raises:
            ValueError: If the update fails.

        Example:
            >>> client.patch_service(
            ...     "service-id-123",
            ...     {"service_url": "https://new-url.example.com/api"}
            ... )
            {'message': 'Service updated successfully'}
        """
        url = f"{self.base_url}/services/{service_id}"
        params = {"server": server}
        try:
            response = self.session.patch(url, json=data, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)

            if "not found" in error_detail.lower():
                raise ValueError("Error updating service: Not found")
            elif "Reserved key" in error_detail:
                raise ValueError(f"Error updating service: {error_detail}")
            else:
                raise ValueError(f"Error updating service: {error_detail}")
