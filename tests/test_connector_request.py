import base64
import importlib.util
import json
from io import BytesIO
from pathlib import Path
import pytest

from app.api.routes import moonshot_explicit


class _Response:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = BytesIO(body)
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._body.read()

    def readline(self) -> bytes:
        return self._body.readline()


def test_json_prompt_is_escaped_before_request() -> None:
    body = moonshot_explicit._build_connector_body(
        {"bodyType": "json", "bodyTemplate": '{"message":"{{ prompt }}"}'},
        'say "hello"',
    )

    assert body is not None
    assert json.loads(body) == {"message": 'say "hello"'}


def test_sse_reader_collects_events_until_done() -> None:
    response = _Response(
        b'data: {"delta":"Hel"}\n\n'
        b'data: {"delta":"lo"}\n\n'
        b'data: [DONE]\n\n'
        b'data: {"delta":"ignored"}\n\n'
    )

    raw = moonshot_explicit._read_connector_response_body(response, "sse")

    assert '"Hel"' in raw
    assert '"lo"' in raw
    assert "ignored" not in raw


def test_sse_json_path_joins_streamed_answer_fragments() -> None:
    raw = (
        'data: {"choices":[{"delta":{"content":"Hel"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"lo"}}]}\n\n'
        "data: [DONE]\n\n"
    )

    extracted = moonshot_explicit._extract_connector_response(
        raw,
        {"type": "json-path", "path": "$.choices.0.delta.content"},
    )

    assert extracted == "Hello"


def test_legacy_sse_event_data_with_path_decodes_answer_fragments() -> None:
    raw = (
        'data: {"content":"Hel"}\n\n'
        'data: {"content":"lo"}\n\n'
        "event: done\n"
        "data: {}\n\n"
    )

    extracted = moonshot_explicit._extract_connector_response(
        raw,
        {"type": "event-data", "path": "$.content"},
    )

    assert extracted == "Hello"


def test_basic_auth_uses_username_and_token_as_password() -> None:
    headers: dict[str, str] = {}

    moonshot_explicit._apply_connector_auth(
        headers,
        {"type": "basic", "username": "alice"},
        "secret",
    )

    encoded = base64.b64encode(b"alice:secret").decode("ascii")
    assert headers["Authorization"] == f"Basic {encoded}"


def test_http_fetch_sends_real_request_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = request.data
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return _Response(b'{"answer":"ok"}')

    monkeypatch.setattr(moonshot_explicit, "open_with_current_network_settings", fake_urlopen)

    result = moonshot_explicit.test_connector(
        {
            "test_prompt": "hello",
            "config": {
                "uri": "https://example.test/chat",
                "token": "token-1",
                "params": {
                    "timeout": 30,
                    "connector_config": {
                        "transport": "http",
                        "auth": {"type": "bearer"},
                        "request": {
                            "method": "POST",
                            "bodyType": "json",
                            "headers": {},
                            "queryParams": {"version": "v1"},
                            "bodyTemplate": '{"message":"{{ prompt }}"}',
                        },
                        "response": {"type": "json-path", "path": "$.answer"},
                    },
                },
            },
        }
    )

    assert result["status"] == "success"
    assert result["rawResponse"] == '{"answer":"ok"}'
    assert result["extractedResponse"] == "ok"
    assert captured == {
        "url": "https://example.test/chat?version=v1",
        "body": b'{"message":"hello"}',
        "authorization": "Bearer token-1",
        "timeout": 30.0,
    }


@pytest.mark.parametrize(
    ("url", "transport"),
    [
        ("file:///etc/passwd", "http"),
        ("https://example.test/socket", "websocket"),
        ("wss://example.test/socket", "sse"),
    ],
)
def test_transport_rejects_incompatible_url_schemes(url: str, transport: str) -> None:
    with pytest.raises(ValueError):
        moonshot_explicit._validate_connector_url(url, transport)


def test_loopback_connector_rejects_redirect_to_public_host() -> None:
    asset = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "integrations"
        / "moonshot"
        / "assets"
        / "configurable-app-connector.py"
    )
    spec = importlib.util.spec_from_file_location(
        "configurable_app_connector_asset",
        asset,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    handler = module._LoopbackOnlyRedirectHandler()
    with pytest.raises(RuntimeError, match="left the approved loopback"):
        handler.redirect_request(
            None,
            None,
            302,
            "Found",
            {},
            "https://example.com/redirected",
        )
