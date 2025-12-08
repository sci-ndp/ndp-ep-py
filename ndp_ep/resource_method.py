"""Resource operations by ID without requiring dataset_id."""

from typing import Any, Dict, Optional

from requests.exceptions import HTTPError

from .client_base import APIClientBase


class APIClientResource(APIClientBase):
    """Extension of APIClientBase with resource operations by ID."""

    def get_resource(
        self,
        resource_id: str,
        server: str = "local",
    ) -> Dict[str, Any]:
        """
        Get a resource by its ID.

        Retrieves a resource using only its ID, without needing the dataset ID.

        Args:
            resource_id: The ID of the resource to retrieve.
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Resource data including id, name, url, description, format,
            and package_id (parent dataset).

        Raises:
            ValueError: If the resource is not found or retrieval fails.

        Example:
            >>> client.get_resource("resource-id-123")
            {'id': 'resource-id-123', 'name': 'data.csv', 'url': '...', ...}
        """
        url = f"{self.base_url}/resource/{resource_id}"
        params = {"server": server}
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError:
            try:
                error_detail = response.json().get(
                    "detail", str(response.text)
                )
            except Exception:
                error_detail = str(response.text)

            if "not found" in error_detail.lower():
                raise ValueError(f"Resource '{resource_id}' not found")
            else:
                raise ValueError(f"Error getting resource: {error_detail}")

    def patch_resource(
        self,
        resource_id: str,
        name: Optional[str] = None,
        url: Optional[str] = None,
        description: Optional[str] = None,
        format: Optional[str] = None,
        server: str = "local",
    ) -> Dict[str, Any]:
        """
        Partially update a resource by its ID.

        Updates only the fields provided, leaving other fields unchanged.
        Does not require knowing the parent dataset ID.

        Args:
            resource_id: The ID of the resource to update.
            name: Optional new name for the resource.
            url: Optional new URL for the resource.
            description: Optional new description.
            format: Optional new format type (CSV, JSON, PDF, etc.).
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Updated resource data.

        Raises:
            ValueError: If the resource is not found or update fails.

        Example:
            >>> client.patch_resource(
            ...     "resource-id-123",
            ...     name="updated-name",
            ...     description="New description"
            ... )
            {'id': 'resource-id-123', 'name': 'updated-name', ...}
        """
        endpoint = f"{self.base_url}/resource/{resource_id}"
        params = {"server": server}

        # Build request data with only provided fields
        data: Dict[str, Any] = {}
        if name is not None:
            data["name"] = name
        if url is not None:
            data["url"] = url
        if description is not None:
            data["description"] = description
        if format is not None:
            data["format"] = format

        try:
            response = self.session.patch(endpoint, json=data, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError:
            try:
                error_detail = response.json().get(
                    "detail", str(response.text)
                )
            except Exception:
                error_detail = str(response.text)

            if "not found" in error_detail.lower():
                raise ValueError(f"Resource '{resource_id}' not found")
            else:
                raise ValueError(f"Error updating resource: {error_detail}")

    def delete_resource(
        self,
        resource_id: str,
        server: str = "local",
    ) -> Dict[str, Any]:
        """
        Delete a resource by its ID using the simplified endpoint.

        Removes the resource without needing to know the parent dataset ID.
        The parent dataset and other resources remain intact.

        Note:
            This method uses the new `/resource/{resource_id}` endpoint.
            For the legacy endpoint that uses query parameters, use
            `delete_resource_by_id()` instead.

        Args:
            resource_id: The ID of the resource to delete.
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Response indicating success.

        Raises:
            ValueError: If the resource is not found or deletion fails.

        Example:
            >>> client.delete_resource("resource-id-123")
            {'message': "Resource 'resource-id-123' deleted successfully"}
        """
        url = f"{self.base_url}/resource/{resource_id}"
        params = {"server": server}
        try:
            response = self.session.delete(url, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError:
            try:
                error_detail = response.json().get(
                    "detail", str(response.text)
                )
            except Exception:
                error_detail = str(response.text)

            if "not found" in error_detail.lower():
                raise ValueError(f"Resource '{resource_id}' not found")
            else:
                raise ValueError(f"Error deleting resource: {error_detail}")

    def search_resources(
        self,
        q: Optional[str] = None,
        name: Optional[str] = None,
        url: Optional[str] = None,
        format: Optional[str] = None,
        description: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        server: str = "local",
    ) -> Dict[str, Any]:
        """
        Search for resources across all datasets.

        Returns resources matching the criteria, with parent dataset context.

        Args:
            q: General search query (searches name, url, description).
            name: Filter by resource name (partial match).
            url: Filter by resource URL (partial match).
            format: Filter by format (CSV, JSON, S3, kafka, etc.).
            description: Filter by description (partial match).
            limit: Maximum results to return (default: 100, max: 1000).
            offset: Number of results to skip for pagination.
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Dictionary with 'count' and 'results'. Each result includes
            resource data plus parent dataset context (dataset_id,
            dataset_name, dataset_title).

        Raises:
            ValueError: If the search fails.

        Example:
            >>> client.search_resources(format="CSV", limit=10)
            {
                'count': 5,
                'results': [
                    {
                        'id': 'res-123',
                        'name': 'data.csv',
                        'format': 'CSV',
                        'dataset_id': 'ds-456',
                        'dataset_name': 'my-dataset',
                        ...
                    },
                    ...
                ]
            }
        """
        endpoint = f"{self.base_url}/resources/search"
        params: Dict[str, Any] = {
            "server": server,
            "limit": limit,
            "offset": offset,
        }

        # Add optional filters
        if q is not None:
            params["q"] = q
        if name is not None:
            params["name"] = name
        if url is not None:
            params["url"] = url
        if format is not None:
            params["format"] = format
        if description is not None:
            params["description"] = description

        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError:
            try:
                error_detail = response.json().get(
                    "detail", str(response.text)
                )
            except Exception:
                error_detail = str(response.text)
            raise ValueError(f"Error searching resources: {error_detail}")
