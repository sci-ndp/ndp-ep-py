"""Tests for resource operations by ID."""

import pytest
import requests_mock

from ndp_ep import APIClient


@pytest.fixture
def client():
    """Create an API client for testing."""
    return APIClient(base_url="http://test-api.com", token="test-token")


class TestGetResource:
    """Tests for get_resource method."""

    def test_get_resource_success(self, client):
        """Test successful resource retrieval."""
        with requests_mock.Mocker() as m:
            mock_response = {
                "id": "res-123",
                "name": "test-resource",
                "url": "https://example.com/data.csv",
                "description": "Test resource",
                "format": "CSV",
                "package_id": "dataset-456",
            }
            m.get(
                "http://test-api.com/resource/res-123?server=local",
                json=mock_response,
            )

            result = client.get_resource("res-123")

            assert result["id"] == "res-123"
            assert result["name"] == "test-resource"
            assert result["format"] == "CSV"
            assert result["package_id"] == "dataset-456"

    def test_get_resource_with_pre_ckan(self, client):
        """Test resource retrieval from pre_ckan server."""
        with requests_mock.Mocker() as m:
            mock_response = {"id": "res-123", "name": "test-resource"}
            m.get(
                "http://test-api.com/resource/res-123?server=pre_ckan",
                json=mock_response,
            )

            result = client.get_resource("res-123", server="pre_ckan")

            assert result["id"] == "res-123"

    def test_get_resource_not_found(self, client):
        """Test resource not found error."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://test-api.com/resource/nonexistent?server=local",
                status_code=404,
                json={"detail": "Resource not found"},
            )

            with pytest.raises(ValueError) as exc_info:
                client.get_resource("nonexistent")

            assert "not found" in str(exc_info.value).lower()


class TestPatchResource:
    """Tests for patch_resource method."""

    def test_patch_resource_success(self, client):
        """Test successful resource update."""
        with requests_mock.Mocker() as m:
            mock_response = {
                "id": "res-123",
                "name": "updated-name",
                "description": "Updated description",
            }
            m.patch(
                "http://test-api.com/resource/res-123?server=local",
                json=mock_response,
            )

            result = client.patch_resource(
                "res-123",
                name="updated-name",
                description="Updated description",
            )

            assert result["name"] == "updated-name"
            assert result["description"] == "Updated description"

            # Verify request body
            request_data = m.last_request.json()
            assert request_data["name"] == "updated-name"
            assert request_data["description"] == "Updated description"

    def test_patch_resource_partial_update(self, client):
        """Test partial resource update with only some fields."""
        with requests_mock.Mocker() as m:
            mock_response = {"id": "res-123", "format": "JSON"}
            m.patch(
                "http://test-api.com/resource/res-123?server=local",
                json=mock_response,
            )

            result = client.patch_resource("res-123", format="JSON")

            assert result["format"] == "JSON"

            # Verify only format was sent
            request_data = m.last_request.json()
            assert "format" in request_data
            assert "name" not in request_data
            assert "url" not in request_data

    def test_patch_resource_not_found(self, client):
        """Test patch on non-existent resource."""
        with requests_mock.Mocker() as m:
            m.patch(
                "http://test-api.com/resource/nonexistent?server=local",
                status_code=404,
                json={"detail": "Resource not found"},
            )

            with pytest.raises(ValueError) as exc_info:
                client.patch_resource("nonexistent", name="new-name")

            assert "not found" in str(exc_info.value).lower()


class TestDeleteResource:
    """Tests for delete_resource method."""

    def test_delete_resource_success(self, client):
        """Test successful resource deletion."""
        with requests_mock.Mocker() as m:
            mock_response = {
                "message": "Resource 'res-123' deleted successfully"
            }
            m.delete(
                "http://test-api.com/resource/res-123?server=local",
                json=mock_response,
            )

            result = client.delete_resource("res-123")

            assert "deleted successfully" in result["message"]

    def test_delete_resource_not_found(self, client):
        """Test deletion of non-existent resource."""
        with requests_mock.Mocker() as m:
            m.delete(
                "http://test-api.com/resource/nonexistent?server=local",
                status_code=404,
                json={"detail": "Resource not found"},
            )

            with pytest.raises(ValueError) as exc_info:
                client.delete_resource("nonexistent")

            assert "not found" in str(exc_info.value).lower()


class TestSearchResources:
    """Tests for search_resources method."""

    def test_search_resources_basic(self, client):
        """Test basic resource search."""
        with requests_mock.Mocker() as m:
            mock_response = {
                "count": 2,
                "results": [
                    {
                        "id": "res-1",
                        "name": "data1.csv",
                        "format": "CSV",
                        "dataset_id": "ds-1",
                        "dataset_name": "dataset-one",
                    },
                    {
                        "id": "res-2",
                        "name": "data2.csv",
                        "format": "CSV",
                        "dataset_id": "ds-2",
                        "dataset_name": "dataset-two",
                    },
                ],
            }
            m.get(
                "http://test-api.com/resources/search",
                json=mock_response,
            )

            result = client.search_resources(format="CSV")

            assert result["count"] == 2
            assert len(result["results"]) == 2
            assert result["results"][0]["format"] == "CSV"

    def test_search_resources_with_query(self, client):
        """Test resource search with general query."""
        with requests_mock.Mocker() as m:
            mock_response = {
                "count": 1,
                "results": [{"id": "res-1", "name": "climate"}],
            }
            m.get(
                "http://test-api.com/resources/search",
                json=mock_response,
            )

            result = client.search_resources(q="climate")

            assert result["count"] == 1
            # Verify query parameter was sent
            assert "q=climate" in m.last_request.url

    def test_search_resources_with_pagination(self, client):
        """Test resource search with pagination."""
        with requests_mock.Mocker() as m:
            mock_response = {"count": 100, "results": []}
            m.get(
                "http://test-api.com/resources/search",
                json=mock_response,
            )

            client.search_resources(limit=50, offset=100)

            # Verify pagination parameters
            assert "limit=50" in m.last_request.url
            assert "offset=100" in m.last_request.url

    def test_search_resources_with_all_filters(self, client):
        """Test resource search with all filter options."""
        with requests_mock.Mocker() as m:
            mock_response = {"count": 0, "results": []}
            m.get(
                "http://test-api.com/resources/search",
                json=mock_response,
            )

            client.search_resources(
                q="test",
                name="data",
                url="example.com",
                format="CSV",
                description="sample",
                limit=10,
                offset=5,
                server="pre_ckan",
            )

            url = m.last_request.url
            assert "q=test" in url
            assert "name=data" in url
            assert "format=CSV" in url
            assert "description=sample" in url
            assert "server=pre_ckan" in url

    def test_search_resources_error(self, client):
        """Test search error handling."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://test-api.com/resources/search",
                status_code=400,
                json={"detail": "Invalid query"},
            )

            with pytest.raises(ValueError) as exc_info:
                client.search_resources(q="test")

            assert "Error searching resources" in str(exc_info.value)
