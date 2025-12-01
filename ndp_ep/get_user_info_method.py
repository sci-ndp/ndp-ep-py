"""User information retrieval functionality."""

from typing import Any, Dict

import requests

from .client_base import APIClientBase


class APIClientUserInfo(APIClientBase):
    """A class to handle requests for user information."""

    def get_user_info(self) -> Dict[str, Any]:
        """
        Get current user information.

        Retrieve detailed information about the currently authenticated user
        from the authentication service. This endpoint requires a valid
        Bearer token.

        Returns:
            User information including roles, groups, username, email, etc.

        Raises:
            ValueError: If the API response contains an error, token is
                invalid, or the service is unreachable.

        Example:
            >>> client = APIClient(base_url="https://api.example.com",
            ...                    token="your-token")
            >>> user = client.get_user_info()
            >>> print(user["username"])
            'john.doe'
        """
        endpoint = f"{self.base_url}/user/info"
        try:
            response = self.session.get(endpoint)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            error_detail = ""
            try:
                error_json = http_err.response.json()
                error_detail = error_json.get("detail", "")
            except (ValueError, AttributeError):
                pass

            if http_err.response.status_code == 401:
                msg = error_detail or "Invalid or missing token"
                raise ValueError(f"Not authenticated: {msg}") from http_err
            elif http_err.response.status_code == 403:
                raise ValueError(
                    f"Forbidden: {error_detail or 'Insufficient permissions'}"
                ) from http_err
            elif http_err.response.status_code == 502:
                raise ValueError(
                    f"Authentication service unavailable: {error_detail}"
                ) from http_err
            else:
                raise ValueError(
                    f"Failed to fetch user info: {http_err}"
                ) from http_err
        except requests.exceptions.RequestException as req_err:
            raise ValueError(
                f"An error occurred while fetching user info: {req_err}"
            ) from req_err
        except ValueError as json_err:
            raise ValueError(
                f"An error occurred while parsing user info: {json_err}"
            ) from json_err
