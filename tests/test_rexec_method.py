from pathlib import Path

import pytest
from requests.exceptions import HTTPError

from ndp_ep.rexec_method import APIClientRexec


class StubRemoteFunc:
    api_urls = []
    environments = []
    remote_addr = None
    remote_port = None

    @classmethod
    def reset(cls):
        cls.api_urls = []
        cls.environments = []
        cls.remote_addr = None
        cls.remote_port = None

    @classmethod
    def set_api_url(cls, url):
        cls.api_urls.append(url)

    @classmethod
    def set_environment(cls, filename, usr_token=None):
        path = Path(filename)
        content = path.read_text()
        cls.environments.append(
            {"path": filename, "token": usr_token, "content": content}
        )

    @classmethod
    def set_remote_addr(cls, addr):
        cls.remote_addr = addr

    @classmethod
    def set_remote_port(cls, port):
        cls.remote_port = port


class FakeResponse:
    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise HTTPError(self.text or "error")

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def get(self, url, params=None):
        self.calls.append({"url": url, "params": params})
        if isinstance(self.responses, dict):
            if url not in self.responses:
                raise AssertionError(f"Unexpected URL requested: {url}")
            return self.responses[url]

        if isinstance(self.responses, list):
            if not self.responses:
                raise AssertionError("No fake responses configured.")
            return self.responses.pop(0)

        return self.responses


class FakeSigningKey:
    def __init__(self, key: str):
        self.key = key


class FakeJWKClient:
    def __init__(self, url: str):
        self.url = url
        self.tokens = []

    def get_signing_key_from_jwt(self, token: str):
        self.tokens.append(token)
        return FakeSigningKey("secret")


def build_client(
    config_payload=None,
    token="CLIENT_TOKEN",
    deployment_api_url="https://api.example.com",
    api_path="/rexec",
    session=None,
):
    deployment_api_url = deployment_api_url.rstrip("/")
    api_path = api_path if api_path.startswith("/") else f"/{api_path}"
    config_payload = config_payload or {}
    client = APIClientRexec.__new__(APIClientRexec)
    client.base_url = "https://api.example.com"
    if session is None:
        status_url = f"{client.base_url}/status/rexec"
        resolved_rexec_url = (
            deployment_api_url
            if deployment_api_url.endswith(api_path)
            else f"{deployment_api_url}{api_path}"
        )
        config_url = f"{resolved_rexec_url.rstrip('/')}/config"
        client.session = FakeSession(
            {
                status_url: FakeResponse({"deployment_api_url": deployment_api_url}),
                config_url: FakeResponse(config_payload),
            }
        )
    else:
        client.session = session
    client.token = token
    return client


def stub_jwt(monkeypatch, module, decoded=None):
    jwk_client = FakeJWKClient("https://jwks.example.com")
    decoded = decoded or {"sub": "user-123"}
    monkeypatch.setattr(module.jwt, "PyJWKClient", lambda url: jwk_client)
    monkeypatch.setattr(
        module.jwt,
        "decode",
        lambda token, key, algorithms, audience, issuer: decoded,
    )
    return jwk_client


def test_setup_rexec_environment_configures_remote_func(monkeypatch, tmp_path):
    import ndp_ep.rexec_method as rexec_module

    StubRemoteFunc.reset()
    monkeypatch.setattr(rexec_module, "_REMOTE_FUNC", StubRemoteFunc)
    stub_jwt(monkeypatch, rexec_module)

    config_payload = {
        "broker_external_host": "broker.example.com",
        "broker_external_port": 30001,
        "api_url": "http://api.example.com/rexec",
    }
    client = build_client(config_payload)

    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("numpy==1.26.0\n")

    result = client.setup_rexec_environment(requirements=requirements_file)

    assert result == config_payload
    assert StubRemoteFunc.api_urls == [
        "https://api.example.com/rexec",
        "http://api.example.com/rexec",
    ]
    env_call = StubRemoteFunc.environments[0]
    assert env_call["token"] == "CLIENT_TOKEN"
    assert env_call["content"] == "numpy==1.26.0\n"
    assert StubRemoteFunc.remote_addr == "broker.example.com"
    assert StubRemoteFunc.remote_port == "30001"

    assert [call["url"] for call in client.session.calls] == [
        "https://api.example.com/status/rexec",
        "https://api.example.com/rexec/config",
    ]
    assert all(call["params"] is None for call in client.session.calls)


def test_setup_rexec_environment_uses_deployment_status(monkeypatch, tmp_path):
    import ndp_ep.rexec_method as rexec_module

    StubRemoteFunc.reset()
    monkeypatch.setattr(rexec_module, "_REMOTE_FUNC", StubRemoteFunc)
    stub_jwt(monkeypatch, rexec_module)

    deployment_api_url = "https://deployment.example.com/rexec"
    client = build_client(
        config_payload={},
        deployment_api_url=deployment_api_url,
    )

    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("numpy==1.26.0\n")

    client.setup_rexec_environment(requirements=requirements_file)

    assert StubRemoteFunc.api_urls == [
        "https://deployment.example.com/rexec",
        "https://deployment.example.com/rexec",
    ]
    assert [call["url"] for call in client.session.calls] == [
        "https://api.example.com/status/rexec",
        "https://deployment.example.com/rexec/config",
    ]


def test_setup_rexec_environment_with_sequence(monkeypatch):
    import ndp_ep.rexec_method as rexec_module

    StubRemoteFunc.reset()
    monkeypatch.setattr(rexec_module, "_REMOTE_FUNC", StubRemoteFunc)
    stub_jwt(monkeypatch, rexec_module)

    config_payload = {
        "broker_external_host": "broker",
        "broker_external_port": 30001,
    }
    client = build_client(config_payload)

    result = client.setup_rexec_environment(
        requirements=["numpy==1.26.0", "scipy==1.12.0"]
    )

    assert result == config_payload
    env_call = StubRemoteFunc.environments[0]
    assert "numpy==1.26.0" in env_call["content"]
    assert "scipy==1.12.0" in env_call["content"]
    # Temporary file should be removed after use
    assert not Path(env_call["path"]).exists()
    assert [call["url"] for call in client.session.calls] == [
        "https://api.example.com/status/rexec",
        "https://api.example.com/rexec/config",
    ]


def test_setup_rexec_environment_requires_remote_func(monkeypatch):
    import ndp_ep.rexec_method as rexec_module

    monkeypatch.setattr(rexec_module, "_REMOTE_FUNC", None)
    client = build_client()

    with pytest.raises(ValueError, match="SciDx-rexec is not installed"):
        client.setup_rexec_environment(requirements=["numpy==1.26.0"])


def test_setup_rexec_environment_invalid_token(monkeypatch):
    import ndp_ep.rexec_method as rexec_module

    StubRemoteFunc.reset()
    monkeypatch.setattr(rexec_module, "_REMOTE_FUNC", StubRemoteFunc)

    def raise_error(*_args, **_kwargs):
        raise RuntimeError("decode failure")

    monkeypatch.setattr(
        rexec_module.jwt, "PyJWKClient", lambda url: FakeJWKClient(url)
    )
    monkeypatch.setattr(rexec_module.jwt, "decode", raise_error)

    client = build_client()

    with pytest.raises(ValueError, match="Invalid token"):
        client.setup_rexec_environment(requirements=["numpy==1.26.0"], token="TOKEN")


def test_setup_rexec_environment_raises_on_config_failure(monkeypatch):
    import ndp_ep.rexec_method as rexec_module

    StubRemoteFunc.reset()
    monkeypatch.setattr(rexec_module, "_REMOTE_FUNC", StubRemoteFunc)
    stub_jwt(monkeypatch, rexec_module)

    status_response = FakeResponse(
        {"deployment_api_url": "https://api.example.com"}
    )
    error_response = FakeResponse({}, status_code=500, text="boom")
    client = build_client(
        session=FakeSession(
            {
                "https://api.example.com/status/rexec": status_response,
                "https://api.example.com/rexec/config": error_response,
            }
        )
    )

    with pytest.raises(ValueError, match="Failed to retrieve Rexec configuration"):
        client.setup_rexec_environment(requirements=["numpy==1.26.0"])
