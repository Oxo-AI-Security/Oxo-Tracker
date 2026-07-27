import json
import threading
import time
from io import BytesIO
from urllib.error import URLError

import pytest

from app.api.routes import moonshot_explicit
from app.services.connector_ai_service import (
    ConnectorAIError,
    ConnectorAIService,
    _PriorityModelScheduler,
    normalize_connector_draft,
    normalize_response_mapping,
)


class _Response:
    def __init__(self, payload: dict) -> None:
        self._body = BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int = -1) -> bytes:
        return self._body.read(limit)


def _draft() -> dict:
    return normalize_connector_draft(
        {
            "name": "Demo Chat",
            "description": "Demo endpoint",
            "transport": "http",
            "uri": "https://example.test/chat",
            "token": "target-secret",
            "auth": {"type": "bearer", "headerName": "Authorization"},
            "request": {
                "method": "POST",
                "headers": {"content-type": "application/json"},
                "queryParams": {},
                "bodyType": "json",
                "formFields": {},
                "bodyTemplate": '{"message":"{{ prompt }}"}',
            },
            "testPrompt": "Hello",
            "missingInformation": [],
        }
    )


def test_qwen_active_settings_are_used_for_connector_generation() -> None:
    captured = {}
    model_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "name": "Demo Chat",
                            "transport": "http",
                            "uri": "https://example.test/chat",
                            "token": "target-secret",
                            "auth": {"type": "bearer", "headerName": "Authorization"},
                            "request": {
                                "method": "POST",
                                "headers": {"content-type": "application/json"},
                                "queryParams": {},
                                "bodyType": "json",
                                "formFields": {},
                                "bodyTemplate": '{"message":"{{ prompt }}"}',
                            },
                            "testPrompt": "Hello",
                            "missingInformation": [],
                        }
                    )
                }
            }
        ]
    }

    def open_request(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _Response(model_payload)

    service = ConnectorAIService(
        settings={
            "provider": "qwen",
            "model": "qwen-plus",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "settings-secret",
        },
        request_open=open_request,
    )

    result = service.generate_draft("curl https://example.test/chat with a JSON message field")

    assert result["missingInformation"] == []
    assert result["config"]["params"]["connector_config"]["request"]["bodyTemplate"] == '{"message":"{{ prompt }}"}'
    assert captured == {
        "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "authorization": "Bearer settings-secret",
        "timeout": 90,
        "payload": {
            "model": "qwen-plus",
            "messages": captured["payload"]["messages"],
            "temperature": 0.1,
            "max_tokens": 4000,
            "response_format": {"type": "json_object"},
        },
    }


def test_ai_connection_refusal_is_retried_without_losing_request() -> None:
    calls = []
    model_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "name": "Retry Chat",
                            "transport": "http",
                            "uri": "https://example.test/chat",
                            "request": {
                                "method": "POST",
                                "bodyType": "json",
                                "bodyTemplate": '{"message":"{{ prompt }}"}',
                            },
                            "missingInformation": [],
                        }
                    )
                }
            }
        ]
    }

    def open_request(request, timeout):
        calls.append((request.full_url, timeout))
        if len(calls) < 3:
            raise URLError(ConnectionRefusedError(10061, "actively refused"))
        return _Response(model_payload)

    service = ConnectorAIService(
        settings={
            "provider": "qwen",
            "model": "qwen-max",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "settings-secret",
        },
        request_open=open_request,
    )

    result = service.generate_draft("POST https://example.test/chat with a JSON message field")

    assert result["config"]["name"] == "Retry Chat"
    assert len(calls) == 3


def test_ai_read_timeout_is_not_retried_three_times() -> None:
    calls = []

    def open_request(request, timeout):
        calls.append((request.full_url, timeout))
        raise TimeoutError("The read operation timed out")

    service = ConnectorAIService(
        settings={
            "provider": "qwen",
            "model": "qwen-max",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key": "settings-secret",
        },
        request_open=open_request,
    )

    with pytest.raises(ConnectorAIError, match="after 1 attempt"):
        service.generate_draft(
            "POST https://example.test/chat with a JSON message field"
        )

    assert len(calls) == 1


def test_priority_scheduler_serves_primary_before_queued_background_work() -> None:
    scheduler = _PriorityModelScheduler(1)
    first_started = threading.Event()
    release_first = threading.Event()
    order: list[str] = []

    def run(label: str, priority: int, hold: bool = False) -> None:
        with scheduler.slot(priority=priority, timeout_seconds=2):
            order.append(label)
            if hold:
                first_started.set()
                release_first.wait(timeout=2)

    first = threading.Thread(target=run, args=("branch-active", 20, True))
    queued_branch = threading.Thread(
        target=run,
        args=("branch-queued", 20),
    )
    primary = threading.Thread(target=run, args=("primary", 0))
    first.start()
    assert first_started.wait(timeout=1)
    queued_branch.start()
    time.sleep(0.02)
    primary.start()
    time.sleep(0.02)
    release_first.set()
    for thread in (first, queued_branch, primary):
        thread.join(timeout=2)

    assert order == ["branch-active", "primary", "branch-queued"]


def test_normalizer_keeps_partial_fields_and_reports_missing_input_mapping() -> None:
    result = normalize_connector_draft(
        {
            "name": "Partial API",
            "uri": "https://example.test/chat",
            "request": {"method": "POST", "bodyType": "json", "bodyTemplate": '{"message":"hello"}'},
        }
    )

    assert result["config"]["name"] == "Partial API"
    assert result["config"]["uri"] == "https://example.test/chat"
    assert any("receives the user's prompt" in item for item in result["missingInformation"])


def test_normalizer_moves_embedded_query_parameters_out_of_request_url() -> None:
    result = normalize_connector_draft(
        {
            "name": "Health Check",
            "uri": "http://127.0.0.1:8001/health?input={{ prompt }}&version=v1",
            "request": {"method": "GET", "queryParams": {"version": "v2"}},
        }
    )

    request = result["config"]["params"]["connector_config"]["request"]
    assert result["config"]["uri"] == "http://127.0.0.1:8001/health"
    assert request["queryParams"] == {"input": "{{ prompt }}", "version": "v2"}


def test_normalizer_removes_captured_messages_after_live_prompt() -> None:
    result = normalize_connector_draft(
        {
            "name": "Captured SSE Chat",
            "transport": "sse",
            "uri": "https://example.test/chat/stream",
            "request": {
                "method": "POST",
                "bodyType": "json",
                "bodyTemplate": {
                    "messages": [
                        {"role": "user", "content": "{{ prompt }}"},
                        {"role": "assistant", "content": "Hello"},
                        {"role": "user", "content": "hi"},
                    ]
                },
            },
        }
    )

    template = result["config"]["params"]["connector_config"]["stream"]["bodyTemplate"]
    assert json.loads(template) == {"messages": [{"role": "user", "content": "{{ prompt }}"}]}


def test_response_mapping_promotes_selected_json_value_to_json_path() -> None:
    mapping = normalize_response_mapping(
        {"type": "text", "selectedText": "ok"},
        '{"status":"ok"}',
    )

    assert mapping["type"] == "json-path"
    assert mapping["path"] == "$.status"


def test_response_mapping_normalizes_sse_event_data_with_json_path() -> None:
    mapping = normalize_response_mapping(
        {"type": "event-data", "path": "$.content"},
        'data: {"content":"Hello"}\n\n',
    )

    assert mapping["type"] == "json-path"
    assert mapping["path"] == "$.content"


def test_ai_configure_route_runs_request_and_maps_output(monkeypatch: pytest.MonkeyPatch) -> None:
    draft = _draft()

    class FakeAIService:
        provider = "qwen"
        model = "qwen-plus"

        def generate_draft(self, _request_information):
            return draft

        def infer_response(self, *, raw_response, extracted_hint=""):
            assert raw_response == '{"answer":"Hello"}'
            return {"type": "json-path", "path": "$.answer", "selectedText": "Hello"}

    monkeypatch.setattr(moonshot_explicit, "ConnectorAIService", FakeAIService)
    monkeypatch.setattr(
        moonshot_explicit,
        "test_connector",
        lambda _data: {
            "status": "success",
            "duration": 10,
            "requestPreview": "{}",
            "rawResponse": '{"answer":"Hello"}',
            "extractedResponse": "",
        },
    )

    result = moonshot_explicit.ai_configure_connector({"request_information": "curl example"})

    assert result["status"] == "completed"
    assert result["testResult"]["extractedResponse"] == "Hello"
    assert result["config"]["params"]["connector_config"]["response"]["path"] == "$.answer"


def test_ai_configure_route_returns_partial_config_when_target_request_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    draft = _draft()

    class FakeAIService:
        provider = "qwen"
        model = "qwen-plus"

        def generate_draft(self, _request_information):
            return draft

    monkeypatch.setattr(moonshot_explicit, "ConnectorAIService", FakeAIService)
    monkeypatch.setattr(
        moonshot_explicit,
        "test_connector",
        lambda _data: {
            "status": "error",
            "duration": 10,
            "requestPreview": "{}",
            "rawResponse": "",
            "extractedResponse": "",
            "error": "HTTP 401: Unauthorized",
        },
    )

    result = moonshot_explicit.ai_configure_connector({"request_information": "curl example"})

    assert result["status"] == "partial"
    assert result["stage"] == "request"
    assert result["config"]["name"] == "Demo Chat"
    assert any("credential" in item for item in result["missingInformation"])
