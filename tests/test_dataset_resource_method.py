"""Tests for dataset resource operations."""

import pytest
import requests_mock

from ndp_ep.dataset_resource_method import APIClientDatasetResource


class TestDatasetResourceMethods:
    """Test dataset resource operations."""

    @pytest.fixture
    def client(self):
        """Create dataset resource client."""
        with requests_mock.Mocker() as m:
            m.get("http://example.com", status_code=200)
            return APIClientDatasetResource(base_url="http://example.com")

    def test_patch_dataset_resource_success(self, client):
        """Test successful resource patch."""
        patch_data = {"name": "updated-name", "description": "New description"}
        expected_response = {
            "id": "resource123",
            "name": "updated-name",
            "description": "New description",
            "url": "https://example.com/data.csv",
            "format": "CSV",
        }

        with requests_mock.Mocker() as m:
            m.patch(
                "http://example.com/dataset/dataset123/resource/resource123",
                json=expected_response,
                status_code=200,
            )

            result = client.patch_dataset_resource(
                "dataset123", "resource123", patch_data
            )
            assert result["id"] == "resource123"
            assert result["name"] == "updated-name"

    def test_patch_dataset_resource_not_found(self, client):
        """Test resource patch when not found."""
        patch_data = {"name": "new-name"}

        with requests_mock.Mocker() as m:
            m.patch(
                "http://example.com/dataset/dataset123/resource/nonexistent",
                json={"detail": "Resource not found"},
                status_code=404,
            )

            with pytest.raises(ValueError, match="Not found"):
                client.patch_dataset_resource(
                    "dataset123", "nonexistent", patch_data
                )

    def test_patch_dataset_resource_error(self, client):
        """Test resource patch with general error."""
        patch_data = {"name": "new-name"}

        with requests_mock.Mocker() as m:
            m.patch(
                "http://example.com/dataset/dataset123/resource/resource123",
                json={"detail": "Invalid format"},
                status_code=400,
            )

            with pytest.raises(ValueError, match="Invalid format"):
                client.patch_dataset_resource(
                    "dataset123", "resource123", patch_data
                )

    def test_delete_dataset_resource_success(self, client):
        """Test successful resource deletion."""
        with requests_mock.Mocker() as m:
            m.delete(
                "http://example.com/dataset/dataset123/resource/resource123",
                json={
                    "message": "Resource 'resource123' deleted successfully"
                },
                status_code=200,
            )

            result = client.delete_dataset_resource(
                "dataset123", "resource123"
            )
            assert "deleted successfully" in result["message"]

    def test_delete_dataset_resource_not_found(self, client):
        """Test resource deletion when not found."""
        with requests_mock.Mocker() as m:
            m.delete(
                "http://example.com/dataset/dataset123/resource/nonexistent",
                json={"detail": "Resource not found"},
                status_code=404,
            )

            with pytest.raises(ValueError, match="Not found"):
                client.delete_dataset_resource("dataset123", "nonexistent")

    def test_delete_dataset_resource_error(self, client):
        """Test resource deletion with general error."""
        with requests_mock.Mocker() as m:
            m.delete(
                "http://example.com/dataset/dataset123/resource/resource123",
                json={"detail": "Cannot delete: resource in use"},
                status_code=400,
            )

            with pytest.raises(ValueError, match="Cannot delete"):
                client.delete_dataset_resource("dataset123", "resource123")

    def test_patch_dataset_resource_with_server(self, client):
        """Test resource patch with pre_ckan server."""
        patch_data = {"url": "https://new-url.com/data.csv"}

        with requests_mock.Mocker() as m:
            m.patch(
                "http://example.com/dataset/dataset123/resource/resource123",
                json={
                    "id": "resource123",
                    "url": "https://new-url.com/data.csv",
                },
                status_code=200,
            )

            result = client.patch_dataset_resource(
                "dataset123", "resource123", patch_data, server="pre_ckan"
            )
            assert result["url"] == "https://new-url.com/data.csv"
            assert m.last_request.qs == {"server": ["pre_ckan"]}
