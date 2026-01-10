"""Remote execution helper methods."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Optional, Sequence, Tuple, Union

from requests.exceptions import HTTPError

from .client_base import APIClientBase

try:
    from rexec.client_api import remote_func as _REMOTE_FUNC
except ImportError:  # pragma: no cover - optional dependency at runtime
    _REMOTE_FUNC = None


class APIClientRexec(APIClientBase):
    """Extension of APIClientBase with remote execution helpers."""

    def setup_rexec_environment(
        self,
        requirements: Union[str, Path, Sequence[str]],
        token: str | None = None,
        *,
        api_path: str = "/rexec",
    ) -> dict[str, Any]:
        """
        Provision and configure a remote execution environment.

        Args:
            requirements: Path to requirements.txt or iterable of requirement
                specifiers.
            token: Optional Keycloak access token for user's identity.
                When omitted, the client token established during
                initialization is used.
            api_path: Relative path to the rexec endpoint. The deployment API
                URL is always resolved from querying the base API
                `/status/rexec` endpoint.

        Returns:
            Dictionary containing the remote execution configuration details.

        Raises:
            ValueError: If SciDx-rexec is not installed, authentication details
                are missing, the token is invalid, or API calls fail.
        """
        remote_func = self._require_remote_func()

        resolved_token = token or self.token
        if not resolved_token:
            raise ValueError(
                "Token is required. Provide a token argument or initialize "
                "the client with an authentication token."
            )

        # rexec_url = "http://localhost:8000/rexec"
        rexec_url = self._resolve_rexec_url(api_path=api_path)
        remote_func.set_api_url(f"{rexec_url}/spawn")

        requirements_path, cleanup = self._prepare_requirements(requirements)
        try:
            remote_func.set_environment(
                str(requirements_path),
                resolved_token,
            )
        finally:
            cleanup()

        broker_config = self._fetch_rexec_broker_config(rexec_url)
        self._configure_remote_func(
            remote_func, broker_config, default_api_url=rexec_url
        )
        return broker_config

    def _require_remote_func(self) -> Any:
        if (
            _REMOTE_FUNC is None
        ):  # pragma: no cover - depends on optional install
            raise ValueError(
                "scidx-rexec is not installed. "
                "Install it to enable remote execution."
            )
        return _REMOTE_FUNC

    def _prepare_requirements(
        self, requirements: Union[str, Path, Sequence[str]]
    ) -> Tuple[Path, Callable[[], None]]:
        """
        Normalise requirements input into a file path consumed by remote_func.
        """
        # if 'requirements' is already a string path, use it directly
        # example: requirements="path/to/requirements.txt"
        if isinstance(requirements, (str, Path)):
            req_path = Path(requirements)
            if not req_path.exists():
                raise ValueError(f"Requirements file not found: {req_path}")
            return req_path, lambda: None

        # if 'requirements' is a sequence of strings, write to a temp file
        # example: reqs = ["pandas==2.2.3", "numpy>=1.26"]
        tmp = NamedTemporaryFile("w", suffix=".txt", delete=False)
        tmp_path = Path(tmp.name)
        try:
            for item in requirements:
                line = str(item).strip()
                if not line or line.startswith("#"):
                    continue
                tmp.write(f"{line}\n")
        finally:
            tmp.close()

        # cleanup function to delete the temp file
        def cleanup() -> None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:  # pragma: no cover - best effort cleanup
                pass

        return tmp_path, cleanup

    def _resolve_rexec_url(self, *, api_path: str) -> str:
        """
        Resolve the final Remote Execution deployment api endpoint URL.
        """
        deployment_api_url = self._fetch_rexec_deployment_api_url()
        path = api_path if api_path.startswith("/") else f"/{api_path}"
        deployment_api_url = deployment_api_url.rstrip("/")

        # Avoid double-appending the path
        # if already included in the deployment URL.
        if deployment_api_url.endswith(path):
            return deployment_api_url

        return f"{deployment_api_url}{path}"

    def _fetch_rexec_deployment_api_url(self) -> str:
        """
        Retrieve the Rexec deployment API base URL
        from the base NDP Endpoint API.
        """
        status_url = f"{self.base_url}/status/rexec"
        response = self.session.get(status_url)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            raise ValueError(
                f"Failed to retrieve Rexec deployment endpoint: "
                f"{response.text or exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(
                "Rexec status endpoint returned invalid JSON."
            ) from exc

        deployment_api_url = payload.get("deployment_api_url")
        if not deployment_api_url:
            raise ValueError(
                "Rexec status endpoint did not provide 'deployment_api_url'."
            )

        return str(deployment_api_url).rstrip("/")

    def _fetch_rexec_broker_config(self, rexec_url: str) -> dict[str, Any]:
        """
        Retrieve broker and API configuration for the remote execution server.
        """
        config_url = f"{rexec_url.rstrip('/')}/broker-config"
        response = self.session.get(config_url)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            raise ValueError(
                f"Failed to retrieve Rexec broker configuration: "
                f"{response.text or exc}"
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(
                "Rexec broker configuration endpoint returned invalid JSON."
            ) from exc

    @staticmethod
    def _configure_remote_func(
        remote_func: Any,
        config: dict[str, Any],
        *,
        default_api_url: str,
    ) -> None:
        """
        Configure the shared remote_func helper with broker and API info.
        """
        # Extract broker address and port from configuration
        broker_addr: Optional[str] = config.get(
            "broker_external_host"
        ) or config.get("broker_addr")
        broker_port: Optional[Union[str, int]] = config.get(
            "broker_external_port"
        ) or config.get("broker_port")
        # Fallback: parse "host:port" formatted external_url
        # if explicit parts missing.
        if (not broker_addr or not broker_port) and config.get(
            "broker_external_url"
        ):
            parts = str(config["broker_external_url"]).split(":")
            if len(parts) >= 2:
                broker_addr = broker_addr or ":".join(parts[:-1])
                broker_port = broker_port or parts[-1]

        # Extract rexec API URL from configuration
        rexec_api_url: Optional[str] = config.get("api_url") or default_api_url

        # Configure the remote_func with broker and API details
        if broker_addr:
            remote_func.set_remote_addr(broker_addr)
        if broker_port:
            remote_func.set_remote_port(str(broker_port))

        remote_func.set_api_url(rexec_api_url)
