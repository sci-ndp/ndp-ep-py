"""Remote execution helper methods."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable, Optional, Sequence, Tuple, Union

import jwt
from requests.exceptions import HTTPError

from .client_base import APIClientBase

try:
    from rexec.client_api import remote_func as _REMOTE_FUNC
except ImportError:  # pragma: no cover - optional dependency at runtime
    _REMOTE_FUNC = None

_DEFAULT_JWKS_URL = (
    "https://idp.nationaldataplatform.org/realms/NDP/"
    "protocol/openid-connect/certs"
)
_DEFAULT_ISSUER = "https://idp.nationaldataplatform.org/realms/NDP"
_DEFAULT_AUDIENCE = "account"


class APIClientRexec(APIClientBase):
    """Extension of APIClientBase with remote execution helpers."""

    def setup_rexec_environment(
        self,
        requirements: Union[str, Path, Sequence[str]],
        token: str | None = None,
        *,
        api_url: str | None = None,
        api_path: str = "/rexec",
        jwks_url: str = _DEFAULT_JWKS_URL,
        issuer: str = _DEFAULT_ISSUER,
        audience: str = _DEFAULT_AUDIENCE,
    ) -> dict:
        """
        Provision and configure a remote execution environment.

        Args:
            requirements: Path to requirements.txt or iterable of requirement
                specifiers.
            token: Optional Keycloak access token containing the user's identity.
                When omitted, the client token established during initialization
                is used.
            api_url: Optional full URL to the rexec endpoint. If omitted,
                the client's base_url combined with `api_path` is used.
            api_path: Relative path to the rexec endpoint when `api_url`
                is not provided.
            jwks_url: URL used to download signing keys for token decoding.
            issuer: Expected issuer for the token.
            audience: Expected audience for the token.

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
                "Token is required. Provide a token argument or initialize the "
                "client with an authentication token."
            )

        user_id = self._decode_user_id(
            resolved_token,
            jwks_url=jwks_url,
            issuer=issuer,
            audience=audience,
        )

        rexec_url = self._build_rexec_url(api_url=api_url, api_path=api_path)
        remote_func.set_api_url(rexec_url)

        requirements_path, cleanup = self._prepare_requirements(requirements)
        try:
            remote_func.set_environment(
                str(requirements_path),
                user_id,
            )
        finally:
            cleanup()

        config = self._fetch_rexec_config(rexec_url)
        self._configure_remote_func(remote_func, config, default_api_url=rexec_url)
        return config

    def _require_remote_func(self):
        if _REMOTE_FUNC is None:  # pragma: no cover - depends on optional install
            raise ValueError(
                "SciDx-rexec is not installed. Install it to enable remote execution."
            )
        return _REMOTE_FUNC

    def _prepare_requirements(
        self, requirements: Union[str, Path, Sequence[str]]
    ) -> Tuple[Path, Callable[[], None]]:
        """
        Normalise requirements input into a file path consumed by remote_func.
        """
        if isinstance(requirements, (str, Path)):
            req_path = Path(requirements)
            if not req_path.exists():
                raise ValueError(f"Requirements file not found: {req_path}")
            return req_path, lambda: None

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

        def cleanup() -> None:
            try:
                tmp_path.unlink()
            except FileNotFoundError:  # pragma: no cover - best effort cleanup
                pass

        return tmp_path, cleanup

    def _decode_user_id(
        self,
        token: str,
        *,
        jwks_url: str,
        issuer: str,
        audience: str,
    ) -> str:
        """
        Decode the Keycloak token and extract the user id.
        """
        try:
            jwks_client = jwt.PyJWKClient(jwks_url)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            decoded = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audience,
                issuer=issuer,
            )
        except Exception as exc:  # pragma: no cover - depends on jwt internals
            raise ValueError("Invalid token provided.") from exc

        user_id = decoded.get("sub")
        if not user_id:
            raise ValueError("Token missing required 'sub' claim.")
        return str(user_id)

    def _build_rexec_url(self, *, api_url: str | None, api_path: str) -> str:
        """
        Resolve the final rexec endpoint URL.
        """
        if api_url:
            return api_url.rstrip("/")
        base = self.base_url.rstrip("/")
        path = api_path if api_path.startswith("/") else f"/{api_path}"
        return f"{base}{path}"

    def _fetch_rexec_config(self, rexec_url: str) -> dict:
        """
        Retrieve broker and API configuration for the remote execution server.
        """
        config_url = f"{rexec_url.rstrip('/')}/config"
        response = self.session.get(config_url)
        try:
            response.raise_for_status()
        except HTTPError as exc:
            raise ValueError(
                f"Failed to retrieve Rexec configuration: {response.text or exc}"
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise ValueError(
                "Rexec configuration endpoint returned invalid JSON."
            ) from exc

    @staticmethod
    def _configure_remote_func(
        remote_func,
        config: dict,
        *,
        default_api_url: str,
    ) -> None:
        """
        Configure the shared remote_func helper with broker and API info.
        """
        broker_addr: Optional[str] = config.get("broker_external_host") or config.get(
            "broker_addr"
        )
        broker_port: Optional[Union[str, int]] = config.get("broker_external_port") or config.get(
            "broker_port"
        )

        # Fallback: parse "host:port" formatted external_url if explicit parts missing.
        if (not broker_addr or not broker_port) and config.get("broker_external_url"):
            parts = str(config["broker_external_url"]).split(":")
            if len(parts) >= 2:
                broker_addr = broker_addr or ":".join(parts[:-1])
                broker_port = broker_port or parts[-1]
        rexec_api_url: Optional[str] = config.get("api_url") or default_api_url

        if broker_addr:
            remote_func.set_remote_addr(broker_addr)
        if broker_port:
            remote_func.set_remote_port(str(broker_port))

        remote_func.set_api_url(rexec_api_url)
