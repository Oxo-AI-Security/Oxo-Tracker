import io
import json
from urllib.error import HTTPError

from app.services.ai_connection_service import probe_ai_connection


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.status = status
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self._body


def test_connection_uses_bearer_auth_and_detects_model() -> None:
    captured = {}

    def open_request(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return FakeResponse({"data": [{"id": "qwen-max"}]})

    result = probe_ai_connection(
        "qwen",
        "qwen-max",
        "https://dashscope.example/v1/",
        "secret-value",
        request_open=open_request,
    )

    assert result["ok"] is True
    assert result["modelAvailable"] is True
    assert captured == {
        "url": "https://dashscope.example/v1/models",
        "authorization": "Bearer secret-value",
        "timeout": 15,
    }


def test_deepseek_connection_uses_openai_compatible_models_endpoint() -> None:
    captured = {}

    def open_request(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse({"data": [{"id": "deepseek-v4-flash"}]})

    result = probe_ai_connection(
        "deepseek",
        "deepseek-v4-flash",
        "https://api.deepseek.com/",
        "deepseek-secret",
        request_open=open_request,
    )

    assert result["ok"] is True
    assert result["modelAvailable"] is True
    assert captured == {
        "url": "https://api.deepseek.com/models",
        "authorization": "Bearer deepseek-secret",
    }


def test_connection_uses_azure_api_key_header() -> None:
    captured = {}

    def open_request(request, timeout):
        captured["api_key"] = request.get_header("Api-key")
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse({"data": []})

    result = probe_ai_connection(
        "azure_openai",
        "deployment-name",
        "https://example.openai.azure.com/openai/v1",
        "azure-secret",
        request_open=open_request,
    )

    assert result["ok"] is True
    assert result["modelAvailable"] is False
    assert captured == {"api_key": "azure-secret", "authorization": None}


def test_connection_returns_safe_authentication_error() -> None:
    def open_request(request, timeout):
        raise HTTPError(request.full_url, 401, "Unauthorized", {}, io.BytesIO())

    result = probe_ai_connection(
        "openai",
        "gpt-5",
        "https://api.openai.com/v1",
        "secret-value",
        request_open=open_request,
    )

    assert result["ok"] is False
    assert result["statusCode"] == 401
    assert result["message"] == "Authentication failed. Check the API key and endpoint."
    assert "secret-value" not in json.dumps(result)
