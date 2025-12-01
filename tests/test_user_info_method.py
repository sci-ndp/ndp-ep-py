"""Tests for user info method."""

import pytest
import requests_mock

from ndp_ep.get_user_info_method import APIClientUserInfo


class TestUserInfoMethod:
    """Test user information retrieval methods."""

    @pytest.fixture
    def user_info_client(self):
        """Create user info client."""
        with requests_mock.Mocker() as m:
            m.get("http://example.com", status_code=200)
            return APIClientUserInfo(base_url="http://example.com")

    def test_get_user_info_success(self, user_info_client):
        """Test successful user info retrieval."""
        expected_info = {
            "roles": ["admin", "user"],
            "groups": ["University Research Group", "researchers"],
            "sub": "user123",
            "username": "john.doe",
            "email": "john.doe@university.edu",
        }

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/user/info",
                json=expected_info,
                status_code=200,
            )

            result = user_info_client.get_user_info()
            assert result == expected_info
            assert result["username"] == "john.doe"
            assert "admin" in result["roles"]

    def test_get_user_info_unauthorized(self, user_info_client):
        """Test user info retrieval with invalid token."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/user/info",
                json={"detail": "Invalid or expired token"},
                status_code=401,
            )

            with pytest.raises(ValueError, match="Not authenticated"):
                user_info_client.get_user_info()

    def test_get_user_info_forbidden(self, user_info_client):
        """Test user info retrieval with insufficient permissions."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/user/info",
                json={"detail": "Token does not have sufficient permissions"},
                status_code=403,
            )

            with pytest.raises(ValueError, match="Forbidden"):
                user_info_client.get_user_info()

    def test_get_user_info_service_unavailable(self, user_info_client):
        """Test user info retrieval when auth service is unavailable."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/user/info",
                json={"detail": "Authentication service is unavailable"},
                status_code=502,
            )

            with pytest.raises(
                ValueError, match="Authentication service unavailable"
            ):
                user_info_client.get_user_info()

    def test_get_user_info_generic_error(self, user_info_client):
        """Test user info retrieval with generic HTTP error."""
        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/user/info",
                json={"detail": "Internal server error"},
                status_code=500,
            )

            with pytest.raises(ValueError, match="Failed to fetch user info"):
                user_info_client.get_user_info()

    def test_get_user_info_minimal_response(self, user_info_client):
        """Test user info with minimal response data."""
        expected_info = {
            "sub": "user456",
            "username": "minimal.user",
        }

        with requests_mock.Mocker() as m:
            m.get(
                "http://example.com/user/info",
                json=expected_info,
                status_code=200,
            )

            result = user_info_client.get_user_info()
            assert result == expected_info
            assert "roles" not in result
            assert "email" not in result
