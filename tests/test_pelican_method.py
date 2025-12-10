"""Tests for Pelican Federation operations."""

import pytest
import requests_mock

from ndp_ep.pelican_method import APIClientPelican


class TestPelicanMethods:
    """Test Pelican Federation operations."""

    @pytest.fixture
    def client(self):
        """Create Pelican client."""
        with requests_mock.Mocker() as m:
            m.get("http://example.com", status_code=200)
            return APIClientPelican(base_url="http://example.com")

    def test_list_federations_success(self, client):
        """Test successful federation listing."""
        expected_response = {
            "success": True,
            "federations": {
                "osdf": {
                    "name": "Open Science Data Federation",
                    "url": "pelican://osg-htc.org",
                    "description": "Primary federation",
                },
                "path-cc": {
                    "name": "PATh Credit Compute",
                    "url": "pelican://path-cc.io",
                    "description": "PATh Facility",
                },
            },
            "count": 2,
        }

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/federations",
                json=expected_response,
                status_code=200,
            )

            result = client.list_federations()
            assert result["success"] is True
            assert result["count"] == 2
            assert "osdf" in result["federations"]

    def test_list_federations_error(self, client):
        """Test federation listing with error."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/federations",
                json={"detail": "Service unavailable"},
                status_code=500,
            )

            with pytest.raises(ValueError, match="Service unavailable"):
                client.list_federations()

    def test_browse_pelican_success(self, client):
        """Test successful namespace browsing."""
        expected_response = {
            "success": True,
            "files": [
                {"name": "data.csv", "type": "file"},
                {"name": "images", "type": "directory"},
            ],
            "count": 2,
        }

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/browse",
                json=expected_response,
                status_code=200,
            )

            result = client.browse_pelican("/ospool/uc-shared/public")
            assert result["success"] is True
            assert result["count"] == 2
            assert m.last_request.qs == {
                "path": ["/ospool/uc-shared/public"],
                "federation": ["osdf"],
                "detail": ["false"],
            }

    def test_browse_pelican_with_detail(self, client):
        """Test browsing with detail flag."""
        expected_response = {
            "success": True,
            "files": [
                {"name": "data.csv", "size": 1024, "modified": "2024-01-01"}
            ],
            "count": 1,
        }

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/browse",
                json=expected_response,
                status_code=200,
            )

            result = client.browse_pelican(
                "/ospool/data", federation="path-cc", detail=True
            )
            assert result["success"] is True
            assert m.last_request.qs == {
                "path": ["/ospool/data"],
                "federation": ["path-cc"],
                "detail": ["true"],
            }

    def test_browse_pelican_not_found(self, client):
        """Test browsing when path not found."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/browse",
                json={"detail": "Path not found"},
                status_code=404,
            )

            with pytest.raises(ValueError, match="Path not found"):
                client.browse_pelican("/nonexistent/path")

    def test_get_pelican_info_success(self, client):
        """Test successful file info retrieval."""
        expected_response = {
            "success": True,
            "name": "data.csv",
            "size": 1024,
            "type": "file",
            "modified": "2024-01-01T12:00:00Z",
        }

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/info",
                json=expected_response,
                status_code=200,
            )

            result = client.get_pelican_info("/ospool/data.csv")
            assert result["success"] is True
            assert result["name"] == "data.csv"
            assert result["size"] == 1024

    def test_get_pelican_info_not_found(self, client):
        """Test file info when not found."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/info",
                json={"detail": "File not found"},
                status_code=404,
            )

            with pytest.raises(ValueError, match="File not found"):
                client.get_pelican_info("/nonexistent/file.csv")

    def test_download_pelican_success(self, client):
        """Test successful file download."""
        file_content = b"column1,column2\nvalue1,value2\n"

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/download",
                content=file_content,
                status_code=200,
            )

            result = client.download_pelican("/ospool/data.csv")
            assert result == file_content
            assert m.last_request.qs == {
                "path": ["/ospool/data.csv"],
                "federation": ["osdf"],
                "stream": ["false"],
            }

    def test_download_pelican_streaming(self, client):
        """Test streaming file download."""
        file_content = b"streaming content"

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/download",
                content=file_content,
                status_code=200,
            )

            result = client.download_pelican("/ospool/data.csv", stream=True)
            # Result is an iterator when streaming
            chunks = list(result)
            assert b"".join(chunks) == file_content
            assert m.last_request.qs["stream"] == ["true"]

    def test_download_pelican_error(self, client):
        """Test download with error."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/pelican/download",
                json={"detail": "Download failed"},
                status_code=500,
            )

            with pytest.raises(ValueError, match="Download failed"):
                client.download_pelican("/ospool/data.csv")

    def test_import_pelican_metadata_success(self, client):
        """Test successful metadata import."""
        expected_response = {
            "success": True,
            "resource": {
                "id": "resource-123",
                "name": "Climate Data",
                "url": "pelican://osg-htc.org/ospool/data.csv",
            },
        }

        with requests_mock.Mocker() as m:
            m.post(
                "http://example.com/pelican/import-metadata",
                json=expected_response,
                status_code=200,
            )

            result = client.import_pelican_metadata(
                pelican_url="pelican://osg-htc.org/ospool/data.csv",
                package_id="my-dataset",
                resource_name="Climate Data",
            )
            assert result["success"] is True
            assert result["resource"]["name"] == "Climate Data"

    def test_import_pelican_metadata_with_description(self, client):
        """Test metadata import with description."""
        expected_response = {
            "success": True,
            "resource": {"id": "resource-123"},
        }

        with requests_mock.Mocker() as m:
            m.post(
                "http://example.com/pelican/import-metadata",
                json=expected_response,
                status_code=200,
            )

            result = client.import_pelican_metadata(
                pelican_url="pelican://osg-htc.org/ospool/data.csv",
                package_id="my-dataset",
                resource_name="Data File",
                resource_description="Climate data from 2024",
            )
            assert result["success"] is True

            # Verify request body
            request_body = m.last_request.json()
            expected_url = "pelican://osg-htc.org/ospool/data.csv"
            assert request_body["pelican_url"] == expected_url
            assert request_body["package_id"] == "my-dataset"
            assert request_body["resource_name"] == "Data File"
            assert (
                request_body["resource_description"]
                == "Climate data from 2024"
            )

    def test_import_pelican_metadata_invalid_url(self, client):
        """Test import with invalid URL."""
        with pytest.raises(ValueError, match="URL must start with pelican://"):
            client.import_pelican_metadata(
                pelican_url="https://example.com/data.csv",
                package_id="my-dataset",
            )

    def test_import_pelican_metadata_error(self, client):
        """Test import with API error."""
        with requests_mock.Mocker() as m:
            m.post(
                "http://example.com/pelican/import-metadata",
                json={"detail": "Package not found"},
                status_code=400,
            )

            with pytest.raises(ValueError, match="Package not found"):
                client.import_pelican_metadata(
                    pelican_url="pelican://osg-htc.org/data.csv",
                    package_id="nonexistent-dataset",
                )
