"""Dataset resource operations functionality."""

from typing import Any, Dict

from requests.exceptions import HTTPError

from .client_base import APIClientBase


class APIClientDatasetResource(APIClientBase):
    """Extension of APIClientBase with dataset resource operations."""

    def patch_dataset_resource(
        self,
        dataset_id: str,
        resource_id: str,
        data: Dict[str, Any],
        server: str = "local",
    ) -> Dict[str, Any]:
        """
        Partially update a resource within a dataset.

        Only updates the fields provided in data, leaving other fields
        unchanged. The dataset itself remains unmodified.

        Args:
            dataset_id: ID or name of the dataset containing the resource.
            resource_id: ID of the resource to update.
            data: Partial data for updating the resource. Can contain:
                - name: Optional new name for the resource
                - url: Optional new URL for the resource
                - description: Optional new description
                - format: Optional new format type (CSV, JSON, PDF, etc.)
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Updated resource data.

        Raises:
            ValueError: If the update fails.

        Example:
            >>> client.patch_dataset_resource(
            ...     "my-dataset",
            ...     "resource-id-123",
            ...     {"name": "updated-name", "description": "New description"}
            ... )
            {'id': 'resource-id-123', 'name': 'updated-name', ...}
        """
        url = f"{self.base_url}/dataset/{dataset_id}/resource/{resource_id}"
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
                raise ValueError("Error updating resource: Not found")
            else:
                raise ValueError(f"Error updating resource: {error_detail}")

    def delete_dataset_resource(
        self,
        dataset_id: str,
        resource_id: str,
        server: str = "local",
    ) -> Dict[str, Any]:
        """
        Delete a resource from a dataset.

        Removes only the specified resource from the dataset. The dataset
        itself and any other resources it contains remain unchanged.

        Args:
            dataset_id: ID or name of the dataset containing the resource.
            resource_id: ID of the resource to delete.
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Response JSON data indicating success.

        Raises:
            ValueError: If the deletion fails.

        Example:
            >>> client.delete_dataset_resource("my-dataset", "resource-id-123")
            {'message': "Resource 'resource-id-123' deleted successfully"}
        """
        url = f"{self.base_url}/dataset/{dataset_id}/resource/{resource_id}"
        params = {"server": server}
        try:
            response = self.session.delete(url, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)

            if "not found" in error_detail.lower():
                raise ValueError("Error deleting resource: Not found")
            else:
                raise ValueError(f"Error deleting resource: {error_detail}")
