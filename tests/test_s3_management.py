"""Tests for S3 buckets and objects management functionality."""

import io
import warnings
from unittest.mock import patch

import pytest
import requests_mock

from ndp_ep.s3_buckets_method import APIClientS3Buckets
from ndp_ep.s3_objects_method import APIClientS3Objects


class TestS3BucketsManagement:
    """Test cases for S3 buckets management."""

    @pytest.fixture
    def mock_api_base(self):
        """Mock the base API URL for testing."""
        return "http://example.com"

    @pytest.fixture
    def s3_buckets_client(self, mock_api_base):
        """Create S3 buckets client for testing."""
        with requests_mock.Mocker() as m:
            m.get(mock_api_base, status_code=200)
            m.get(
                f"{mock_api_base}/status/",
                json={"version": "0.2.0"},
                status_code=200,
            )
            return APIClientS3Buckets(base_url=mock_api_base, token="test-token")

    def test_list_buckets_success(self, s3_buckets_client, mock_api_base):
        """Test successful bucket listing."""
        with requests_mock.Mocker() as m:
            expected_buckets = [
                {"name": "bucket1", "created": "2024-01-01"},
                {"name": "bucket2", "created": "2024-01-02"},
            ]
            m.get(f"{mock_api_base}/s3/buckets/", json=expected_buckets, status_code=200)

            result = s3_buckets_client.list_buckets()
            assert result == expected_buckets

    def test_list_buckets_error(self, s3_buckets_client, mock_api_base):
        """Test bucket listing error handling."""
        with requests_mock.Mocker() as m:
            m.get(
                f"{mock_api_base}/s3/buckets/",
                json={"detail": "Access denied"},
                status_code=403,
            )

            with pytest.raises(ValueError, match="Error listing S3 buckets"):
                s3_buckets_client.list_buckets()

    def test_create_bucket_success(self, s3_buckets_client, mock_api_base):
        """Test successful bucket creation."""
        with requests_mock.Mocker() as m:
            expected_response = {"name": "test-bucket", "status": "created"}
            m.post(f"{mock_api_base}/s3/buckets/", json=expected_response, status_code=201)

            result = s3_buckets_client.create_bucket("test-bucket")
            assert result == expected_response

    def test_create_bucket_error(self, s3_buckets_client, mock_api_base):
        """Test bucket creation error handling."""
        with requests_mock.Mocker() as m:
            m.post(
                f"{mock_api_base}/s3/buckets/",
                json={"detail": "Bucket already exists"},
                status_code=409,
            )

            with pytest.raises(ValueError, match="Error creating S3 bucket"):
                s3_buckets_client.create_bucket("existing-bucket")

    def test_get_bucket_info_success(self, s3_buckets_client, mock_api_base):
        """Test successful bucket info retrieval."""
        with requests_mock.Mocker() as m:
            expected_info = {
                "name": "test-bucket",
                "created": "2024-01-01",
                "size": "1.2GB",
                "objects": 42,
            }
            m.get(
                f"{mock_api_base}/s3/buckets/test-bucket", json=expected_info, status_code=200
            )

            result = s3_buckets_client.get_bucket_info("test-bucket")
            assert result == expected_info

    def test_get_bucket_info_not_found(self, s3_buckets_client, mock_api_base):
        """Test bucket info when bucket doesn't exist."""
        with requests_mock.Mocker() as m:
            m.get(
                f"{mock_api_base}/s3/buckets/nonexistent",
                json={"detail": "Bucket not found"},
                status_code=404,
            )

            with pytest.raises(ValueError, match="S3 bucket 'nonexistent' not found"):
                s3_buckets_client.get_bucket_info("nonexistent")

    def test_delete_bucket_success(self, s3_buckets_client, mock_api_base):
        """Test successful bucket deletion."""
        with requests_mock.Mocker() as m:
            expected_response = {"message": "Bucket deleted successfully"}
            m.delete(
                f"{mock_api_base}/s3/buckets/test-bucket",
                json=expected_response,
                status_code=200,
            )

            result = s3_buckets_client.delete_bucket("test-bucket")
            assert result == expected_response

    def test_delete_bucket_not_found(self, s3_buckets_client, mock_api_base):
        """Test bucket deletion when bucket doesn't exist."""
        with requests_mock.Mocker() as m:
            m.delete(
                f"{mock_api_base}/s3/buckets/nonexistent",
                json={"detail": "Bucket not found"},
                status_code=404,
            )

            with pytest.raises(ValueError, match="S3 bucket 'nonexistent' not found"):
                s3_buckets_client.delete_bucket("nonexistent")


class TestS3ObjectsManagement:
    """Test cases for S3 objects management."""

    @pytest.fixture
    def mock_api_base(self):
        """Mock the base API URL for testing."""
        return "http://example.com"

    @pytest.fixture
    def s3_objects_client(self, mock_api_base):
        """Create S3 objects client for testing."""
        with requests_mock.Mocker() as m:
            m.get(mock_api_base, status_code=200)
            m.get(
                f"{mock_api_base}/status/",
                json={"version": "0.2.0"},
                status_code=200,
            )
            return APIClientS3Objects(base_url=mock_api_base, token="test-token")

    def test_list_objects_success(self, s3_objects_client, mock_api_base):
        """Test successful objects listing."""
        with requests_mock.Mocker() as m:
            expected_objects = [
                {"key": "file1.txt", "size": 1024, "modified": "2024-01-01"},
                {"key": "file2.csv", "size": 2048, "modified": "2024-01-02"},
            ]
            m.get(
                f"{mock_api_base}/s3/objects/test-bucket",
                json=expected_objects,
                status_code=200,
            )

            result = s3_objects_client.list_objects("test-bucket")
            assert result == expected_objects

    def test_list_objects_with_prefix(self, s3_objects_client, mock_api_base):
        """Test objects listing with prefix filter."""
        with requests_mock.Mocker() as m:
            expected_objects = [{"key": "data/file1.txt", "size": 1024}]
            m.get(
                f"{mock_api_base}/s3/objects/test-bucket",
                json=expected_objects,
                status_code=200,
            )

            result = s3_objects_client.list_objects("test-bucket", prefix="data/")
            assert result == expected_objects
            # Check that prefix was passed as parameter
            assert m.last_request.qs["prefix"] == ["data/"]

    def test_download_object_success(self, s3_objects_client, mock_api_base):
        """Test successful object download."""
        with requests_mock.Mocker() as m:
            expected_content = b"test file content"
            m.get(
                f"{mock_api_base}/s3/objects/test-bucket/test-file.txt",
                content=expected_content,
                status_code=200,
            )

            result = s3_objects_client.download_object("test-bucket", "test-file.txt")
            assert result == expected_content

    def test_download_object_not_found(self, s3_objects_client, mock_api_base):
        """Test object download when object doesn't exist."""
        with requests_mock.Mocker() as m:
            m.get(
                f"{mock_api_base}/s3/objects/test-bucket/nonexistent.txt",
                json={"detail": "Object not found"},
                status_code=404,
            )

            with pytest.raises(
                ValueError, match="S3 object 'nonexistent.txt' not found in bucket 'test-bucket'"
            ):
                s3_objects_client.download_object("test-bucket", "nonexistent.txt")

    def test_delete_object_success(self, s3_objects_client, mock_api_base):
        """Test successful object deletion."""
        with requests_mock.Mocker() as m:
            expected_response = {"message": "Object deleted successfully"}
            m.delete(
                f"{mock_api_base}/s3/objects/test-bucket/test-file.txt",
                json=expected_response,
                status_code=200,
            )

            result = s3_objects_client.delete_object("test-bucket", "test-file.txt")
            assert result == expected_response

    def test_get_object_metadata_success(self, s3_objects_client, mock_api_base):
        """Test successful object metadata retrieval."""
        with requests_mock.Mocker() as m:
            expected_metadata = {
                "key": "test-file.txt",
                "size": 1024,
                "content_type": "text/plain",
                "modified": "2024-01-01T12:00:00Z",
            }
            m.get(
                f"{mock_api_base}/s3/objects/test-bucket/test-file.txt/metadata",
                json=expected_metadata,
                status_code=200,
            )

            result = s3_objects_client.get_object_metadata("test-bucket", "test-file.txt")
            assert result == expected_metadata

    def test_generate_presigned_upload_url_success(self, s3_objects_client, mock_api_base):
        """Test successful presigned upload URL generation."""
        with requests_mock.Mocker() as m:
            expected_response = {
                "url": "https://s3.amazonaws.com/test-bucket",
                "fields": {"key": "test-file.txt", "policy": "base64policy"},
            }
            m.post(
                f"{mock_api_base}/s3/objects/test-bucket/test-file.txt/presigned-upload",
                json=expected_response,
                status_code=200,
            )

            result = s3_objects_client.generate_presigned_upload_url(
                "test-bucket", "test-file.txt"
            )
            assert result == expected_response

    def test_generate_presigned_download_url_success(self, s3_objects_client, mock_api_base):
        """Test successful presigned download URL generation."""
        with requests_mock.Mocker() as m:
            expected_response = {"url": "https://s3.amazonaws.com/test-bucket/test-file.txt?signature=abc"}
            m.post(
                f"{mock_api_base}/s3/objects/test-bucket/test-file.txt/presigned-download",
                json=expected_response,
                status_code=200,
            )

            result = s3_objects_client.generate_presigned_download_url(
                "test-bucket", "test-file.txt"
            )
            assert result == expected_response

    def test_generate_presigned_urls_with_expiration(self, s3_objects_client, mock_api_base):
        """Test presigned URL generation with custom expiration."""
        with requests_mock.Mocker() as m:
            expected_response = {"url": "https://s3.amazonaws.com/test-bucket/test-file.txt"}
            m.post(
                f"{mock_api_base}/s3/objects/test-bucket/test-file.txt/presigned-upload",
                json=expected_response,
                status_code=200,
            )

            result = s3_objects_client.generate_presigned_upload_url(
                "test-bucket", "test-file.txt", expiration=3600
            )
            assert result == expected_response
            # Verify expiration was passed in request
            request_data = m.last_request.json()
            assert request_data["expiration"] == 3600