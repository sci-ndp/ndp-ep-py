"""Pelican Federation operations functionality."""

from typing import Any, Dict, Iterator, Optional, Union

from requests.exceptions import HTTPError

from .client_base import APIClientBase


class APIClientPelican(APIClientBase):
    """Extension of APIClientBase with Pelican Federation operations."""

    def list_federations(self) -> Dict[str, Any]:
        """
        List available Pelican federations.

        Returns:
            Dictionary containing available federations with their URLs
            and descriptions.

        Raises:
            ValueError: If unable to retrieve federations.

        Example:
            >>> client.list_federations()
            {'success': True, 'federations': {...}, 'count': 2}
        """
        endpoint = f"{self.base_url}/pelican/federations"
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise ValueError(f"Error listing federations: {error_detail}")

    def browse_pelican(
        self,
        path: str,
        federation: str = "osdf",
        detail: bool = False,
    ) -> Dict[str, Any]:
        """
        Browse files in a Pelican federation namespace.

        Args:
            path: Namespace path to browse (e.g., "/ospool/uc-shared/public").
            federation: Federation name (default "osdf").
            detail: If True, return detailed file information.

        Returns:
            Dictionary containing files in the namespace.

        Raises:
            ValueError: If path not found or browsing fails.

        Example:
            >>> client.browse_pelican("/ospool/uc-shared/public")
            {'success': True, 'files': [...], 'count': 10}
        """
        endpoint = f"{self.base_url}/pelican/browse"
        params = {
            "path": path,
            "federation": federation,
            "detail": str(detail).lower(),
        }
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)

            if response.status_code == 404:
                raise ValueError(f"Path not found: {path}")
            raise ValueError(f"Error browsing Pelican: {error_detail}")

    def get_pelican_info(
        self,
        path: str,
        federation: str = "osdf",
    ) -> Dict[str, Any]:
        """
        Get metadata for a file without downloading it.

        Args:
            path: File path in the federation.
            federation: Federation name (default "osdf").

        Returns:
            Dictionary containing file metadata (name, size, type, etc.).

        Raises:
            ValueError: If file not found or request fails.

        Example:
            >>> client.get_pelican_info("/ospool/uc-shared/public/data.csv")
            {'success': True, 'name': 'data.csv', 'size': 1024, ...}
        """
        endpoint = f"{self.base_url}/pelican/info"
        params = {
            "path": path,
            "federation": federation,
        }
        try:
            response = self.session.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)

            if response.status_code == 404:
                raise ValueError(f"File not found: {path}")
            raise ValueError(f"Error getting Pelican info: {error_detail}")

    def download_pelican(
        self,
        path: str,
        federation: str = "osdf",
        stream: bool = False,
    ) -> Union[bytes, Iterator[bytes]]:
        """
        Download a file from Pelican federation.

        Args:
            path: File path to download.
            federation: Federation name (default "osdf").
            stream: If True, return an iterator for streaming content;
                if False, return entire file content as bytes.

        Returns:
            File contents as bytes, or iterator of bytes if stream=True.

        Raises:
            ValueError: If download fails.

        Example:
            >>> content = client.download_pelican("/ospool/data.csv")
            >>> with open("data.csv", "wb") as f:
            ...     f.write(content)

            # Streaming download
            >>> for chunk in client.download_pelican("/ospool/data.csv",
            ...                                       stream=True):
            ...     process(chunk)
        """
        endpoint = f"{self.base_url}/pelican/download"
        params = {
            "path": path,
            "federation": federation,
            "stream": str(stream).lower(),
        }
        try:
            response = self.session.get(endpoint, params=params, stream=stream)
            response.raise_for_status()

            if stream:
                return response.iter_content(chunk_size=8192)
            return response.content
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise ValueError(f"Error downloading from Pelican: {error_detail}")

    def import_pelican_metadata(
        self,
        pelican_url: str,
        package_id: str,
        resource_name: Optional[str] = None,
        resource_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import a Pelican file as a resource in the local catalog.

        This allows registering external Pelican files in the local catalog
        so they appear in searches and can be managed alongside local resources.

        Args:
            pelican_url: Full Pelican URL (e.g., "pelican://osg-htc.org/path").
            package_id: ID of the dataset to add the resource to.
            resource_name: Optional name for the resource.
            resource_description: Optional description for the resource.

        Returns:
            Dictionary containing the created resource data.

        Raises:
            ValueError: If URL is invalid or import fails.

        Example:
            >>> client.import_pelican_metadata(
            ...     pelican_url="pelican://osg-htc.org/ospool/data.csv",
            ...     package_id="my-dataset",
            ...     resource_name="Climate Data"
            ... )
            {'success': True, 'resource': {...}}
        """
        if not pelican_url.startswith("pelican://"):
            raise ValueError("URL must start with pelican://")

        endpoint = f"{self.base_url}/pelican/import-metadata"
        payload: Dict[str, Any] = {
            "pelican_url": pelican_url,
            "package_id": package_id,
        }
        if resource_name is not None:
            payload["resource_name"] = resource_name
        if resource_description is not None:
            payload["resource_description"] = resource_description

        try:
            response = self.session.post(endpoint, json=payload)
            response.raise_for_status()
            return response.json()
        except HTTPError as e:
            try:
                error_detail = response.json().get("detail", str(e))
            except Exception:
                error_detail = str(e)
            raise ValueError(
                f"Error importing Pelican metadata: {error_detail}"
            )
