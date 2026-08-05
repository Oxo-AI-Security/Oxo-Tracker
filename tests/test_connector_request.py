import importlib.util
import json
from io import BytesIO
from pathlib import Path
import pytest

from app.api.routes import moonshot_explicit


class _Response:
    def __init__(self, body: bytes, status: int = 200, content_type: str = "") -> None:
        self._body = BytesIO(body)
        self.status = status
        self.headers = {"Content-Type": content_type} if content_type else {}

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


def test_multipart_prompt_uses_matching_generated_boundary() -> None:
    request_config = {
        "bodyType": "multipart",
        "formFields": {
            "industry": "consumer",
            "requirement": "{{ prompt }}",
            "fileUp": "",
        },
    }
    body = moonshot_explicit._build_connector_body(request_config, "safe test")
    headers = {"Content-Type": "multipart/form-data; boundary=stale-browser-boundary"}

    moonshot_explicit._apply_content_type(headers, request_config, body)

    content_type = headers["Content-Type"]
    boundary = content_type.split("boundary=", 1)[1]
    assert body is not None
    assert f"--{boundary}\r\n".encode() in body
    assert b'name="requirement"\r\n\r\nsafe test\r\n' in body
    assert b'name="fileUp"\r\n\r\n\r\n' in body
    assert b"stale-browser-boundary" not in body


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


def test_transport_detection_uses_response_content_type_and_event_framing() -> None:
    assert moonshot_explicit._detect_connector_transport("http", "text/event-stream; charset=utf-8") == "sse"
    assert moonshot_explicit._detect_connector_transport("http", "application/octet-stream", "data: hello\n\n") == "sse"
    assert moonshot_explicit._detect_connector_transport("sse", "application/json", '{"answer":"ok"}') == "http"


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


def test_http_json_sequence_extracts_selected_path_from_last_document() -> None:
    raw = (
        '{"history_metadata":{"title":"Initial Greeting"}}\n'
        '{"choices":[{"messages":[{"role":"assistant","content":"Final answer"}]}]}'
    )

    extracted = moonshot_explicit._extract_connector_response(
        raw,
        {"type": "json-path", "path": "$.choices.0.messages.0.content"},
    )

    assert extracted == "Final answer"


def test_legacy_text_fragment_sample_migrates_to_json_path_at_runtime() -> None:
    sample = (
        '{"history_metadata":{"title":"Initial Greeting"}}\n'
        '{"choices":[{"messages":[{"role":"assistant","content":"{{ output }}"}]}]}'
    )
    raw = (
        '{"history_metadata":{"title":"Initial Greeting"}}\n'
        '{"choices":[{"messages":[{"role":"assistant","content":"Current answer"}]}]}'
    )

    extracted = moonshot_explicit._extract_connector_response(
        raw,
        {
            "type": "text-fragment",
            "selectedText": "Old answer",
            "sampleResponse": sample,
        },
    )

    assert extracted == "Current answer"


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
                "params": {
                    "timeout": 30,
                    "connector_config": {
                        "transport": "http",
                        "request": {
                            "method": "POST",
                            "bodyType": "json",
                            "headers": {"Authorization": "Bearer token-1"},
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


def test_runtime_asset_builds_multipart_body_with_matching_boundary() -> None:
    asset = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "integrations"
        / "moonshot"
        / "assets"
        / "configurable-app-connector.py"
    )
    spec = importlib.util.spec_from_file_location("configurable_app_connector_asset_multipart", asset)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    connector = object.__new__(module.ConfigurableAppConnector)
    request_config = {
        "bodyType": "multipart",
        "formFields": {"message": "{{ prompt }}"},
    }
    body = connector._build_body(request_config, "hello")
    headers = {"content-type": "multipart/form-data; boundary=old"}

    connector._apply_content_type(headers, request_config, body)

    boundary = headers["content-type"].split("boundary=", 1)[1]
    assert f"--{boundary}\r\n".encode() in body
    assert b'name="message"\r\n\r\nhello\r\n' in body
    assert connector._read_json_path({"items": []}, "$.items.4.answer") is None


def test_runtime_asset_extracts_json_sequence_without_raw_response_fallback() -> None:
    asset = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "integrations"
        / "moonshot"
        / "assets"
        / "configurable-app-connector.py"
    )
    spec = importlib.util.spec_from_file_location("configurable_app_connector_asset_json_sequence", asset)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    connector = object.__new__(module.ConfigurableAppConnector)
    connector.config = {
        "response": {"type": "json-path", "path": "$.choices.0.messages.0.content"}
    }
    raw = (
        '{"history_metadata":{"title":"Initial Greeting"}}\n'
        '{"choices":[{"messages":[{"role":"assistant","content":"Final answer"}]}]}'
    )

    assert connector._extract_response(raw) == "Final answer"


def test_runtime_asset_migrates_legacy_text_fragment_sample_to_json_path() -> None:
    asset = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "integrations"
        / "moonshot"
        / "assets"
        / "configurable-app-connector.py"
    )
    spec = importlib.util.spec_from_file_location("configurable_app_connector_asset_legacy_mapping", asset)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    connector = object.__new__(module.ConfigurableAppConnector)
    connector.config = {
        "response": {
            "type": "text-fragment",
            "selectedText": "Old answer",
            "sampleResponse": (
                '{"history_metadata":{"title":"Initial Greeting"}}\n'
                '{"choices":[{"messages":[{"content":"{{ output }}"}]}]}'
            ),
        }
    }
    raw = (
        '{"history_metadata":{"title":"Initial Greeting"}}\n'
        '{"choices":[{"messages":[{"content":"Current answer"}]}]}'
    )

    assert connector._extract_response(raw) == "Current answer"
