"""S3 resource update functionality."""

from typing import Any, Dict

from requests.exceptions import HTTPError

from .client_base import APIClientBase


class APIClientS3Update(APIClientBase):
    """Extension of APIClientBase with S3 resource update method."""

    def update_s3_resource(
        self, resource_id: str, data: Dict[str, Any], server: str = "local"
    ) -> Dict[str, Any]:
        """
        Update an existing S3 resource by making a PUT request.

        Args:
            resource_id: ID of the resource to update.
            data: Data for updating the S3 resource. Can contain:
                - resource_name: Optional unique name of the resource
                - resource_title: Optional title of the resource
                - owner_org: Optional ID of the organization
                - resource_s3: Optional S3 URL of the resource
                - notes: Optional additional notes
                - extras: Optional additional metadata
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Response JSON data indicating success.

        Raises:
            ValueError: If the update fails.
        """
        url = f"{self.base_url}/s3/{resource_id}"
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

            if "S3 resource not found" in error_detail:
                raise ValueError("Error updating S3 resource: Not found")
            else:
                raise ValueError(f"Error updating S3 resource: {error_detail}")

    def patch_s3_resource(
        self, resource_id: str, data: Dict[str, Any], server: str = "local"
    ) -> Dict[str, Any]:
        """
        Partially update an existing S3 resource by making a PATCH request.

        Only updates the fields provided in data, leaving other fields
        unchanged. This is useful when you only want to modify specific
        attributes without affecting the rest of the S3 resource.

        Args:
            resource_id: ID of the resource to update.
            data: Partial data for updating the S3 resource. Can contain:
                - resource_name: Optional unique name of the resource
                - resource_title: Optional title of the resource
                - owner_org: Optional ID of the organization
                - resource_s3: Optional S3 URL of the resource
                - notes: Optional additional notes
                - extras: Optional additional metadata (merged with existing)
            server: Specify 'local' or 'pre_ckan'. Defaults to 'local'.

        Returns:
            Response JSON data indicating success.

        Raises:
            ValueError: If the update fails.

        Example:
            >>> client.patch_s3_resource(
            ...     "resource-id-123",
            ...     {"resource_title": "Updated Title"}
            ... )
            {'message': 'S3 resource updated successfully'}
        """
        url = f"{self.base_url}/s3/{resource_id}"
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
                raise ValueError("Error updating S3 resource: Not found")
            elif "Reserved key" in error_detail:
                raise ValueError(f"Error updating S3 resource: {error_detail}")
            else:
                raise ValueError(f"Error updating S3 resource: {error_detail}")
