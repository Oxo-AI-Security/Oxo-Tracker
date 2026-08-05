import asyncio
import hashlib
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from fastapi import APIRouter, Body, HTTPException

from app.services.connector_ai_service import ConnectorAIError, ConnectorAIService
from app.services.http_transport import open_with_current_network_settings
from app.services.moonshot_api_service import MoonshotApiService
from app.services.redteam_sensitive_information_service import (
    RedTeamSensitiveInformationService,
    SensitiveInformationAnalysisError,
)
from app.services.redteam_task_agent_service import (
    RedTeamTaskAgentService,
    TaskAgentServiceError,
)

router = APIRouter(prefix="/moonshot", tags=["Moonshot Explicit API"])
logger = logging.getLogger(__name__)
REDTEAM_DATA_DIR = Path("data/redteam_sessions")


def service() -> MoonshotApiService:
    """创建 Moonshot 服务实例，后续可替换成依赖注入容器。"""
    return MoonshotApiService()


def _redteam_session_path(session_id: str) -> Path:
    safe_id = "".join(char for char in session_id if char.isalnum() or char in ("-", "_"))[:120]
    if not safe_id:
        raise HTTPException(status_code=400, detail="Invalid session id.")
    return REDTEAM_DATA_DIR / safe_id / "session.json"


@router.get("/redteam/local-sessions", summary="List persisted red-team chat sessions")
def list_local_redteam_sessions():
    REDTEAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    sessions = []
    for session_file in sorted(REDTEAM_DATA_DIR.glob("*/session.json")):
        try:
            sessions.append(json.loads(session_file.read_text(encoding="utf-8")))
        except Exception:
            continue
    return sessions


@router.put("/redteam/local-sessions/{session_id}", summary="Persist a red-team chat session")
def save_local_redteam_session(session_id: str, data: dict[str, Any] = Body(...)):
    path = _redteam_session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**data, "id": session_id}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"saved": True, "session_id": session_id}


@router.delete("/redteam/local-sessions/{session_id}", summary="Delete a persisted red-team chat session")
def delete_local_redteam_session(session_id: str):
    path = _redteam_session_path(session_id)
    if path.parent.exists():
        shutil.rmtree(path.parent)
    return {"deleted": True, "session_id": session_id}


@router.post(
    "/redteam/analyze-sensitive-information",
    summary="Analyze one completed red-team turn with the active Settings AI model",
)
def analyze_redteam_sensitive_information(data: dict[str, Any] = Body(...)) -> dict[str, Any]:
    user_input = str(data.get("user_input") or "")
    assistant_output = str(data.get("assistant_output") or "")
    try:
        ai_service = RedTeamSensitiveInformationService()
        try:
            result = ai_service.analyze_turn(
                user_input=user_input,
                assistant_output=assistant_output,
                force_model=True,
            )
        except TypeError as error:
            if "force_model" not in str(error):
                raise
            result = ai_service.analyze_turn(
                user_input=user_input,
                assistant_output=assistant_output,
            )
        return {
            **result,
            "provider": ai_service.provider,
            "model": ai_service.model,
        }
    except SensitiveInformationAnalysisError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def _task_agent_response(service: RedTeamTaskAgentService, result: dict[str, Any]) -> dict[str, Any]:
    return {
        **result,
        "provider": service.provider,
        "model": service.model,
    }


@router.post(
    "/redteam/task-agent/plan",
    summary="Generate the next interaction plan with the active Settings AI model",
)
def plan_redteam_task_agent_interaction(data: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        task_agent = RedTeamTaskAgentService()
        max_rounds = data.get("max_rounds")
        result = task_agent.plan(
            goal=str(data.get("goal") or ""),
            history=data.get("history"),
            round_number=int(data.get("round") or 1),
            max_rounds=int(max_rounds) if max_rounds is not None else None,
            previous_evaluation=data.get("previous_evaluation"),
        )
        return _task_agent_response(task_agent, result)
    except (TaskAgentServiceError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/redteam/task-agent/execute",
    summary="Turn a planner plan into one target interaction message",
)
def execute_redteam_task_agent_interaction(data: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        task_agent = RedTeamTaskAgentService()
        result = task_agent.execute(
            goal=str(data.get("goal") or ""),
            history=data.get("history"),
            plan=data.get("plan"),
        )
        return _task_agent_response(task_agent, result)
    except TaskAgentServiceError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post(
    "/redteam/task-agent/evaluate",
    summary="Evaluate goal progress for one completed task-agent turn",
)
def evaluate_redteam_task_agent_progress(data: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        task_agent = RedTeamTaskAgentService()
        max_rounds = data.get("max_rounds")
        result = task_agent.evaluate(
            goal=str(data.get("goal") or ""),
            history=data.get("history"),
            latest_user_input=str(data.get("latest_user_input") or ""),
            latest_assistant_output=str(data.get("latest_assistant_output") or ""),
            success_criteria=data.get("success_criteria"),
            round_number=int(data.get("round") or 1),
            max_rounds=int(max_rounds) if max_rounds is not None else None,
        )
        return _task_agent_response(task_agent, result)
    except (TaskAgentServiceError, TypeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


def handle_call(callable_result):
    """统一处理 Moonshot 异常，避免原始异常直接泄漏到接口层。"""
    try:
        return callable_result()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# 连接器
@router.post("/connectors/from-endpoint", summary="根据端点创建连接器")
def create_connector_from_endpoint(ep_id: str = Body(..., embed=True)):
    """根据端点 ID 创建连接器，通常用于调试 endpoint 是否能加载。"""
    return handle_call(lambda: service().create_connector_from_endpoint(ep_id))


@router.post("/connectors/from-endpoints", summary="批量根据端点创建连接器")
def create_connectors_from_endpoints(ep_ids: list[str] = Body(..., embed=True)):
    """根据多个端点 ID 批量创建连接器。"""
    return handle_call(lambda: service().create_connectors_from_endpoints(ep_ids))


@router.get("/connectors/types", summary="获取全部连接器类型")
def get_all_connector_type():
    """获取当前 moonshot-data 中可用的连接器类型。"""
    return handle_call(lambda: service().get_all_connector_type())


# 端点
@router.post("/connectors/test", summary="Test configurable connector endpoint")
def test_connector(data: dict[str, Any] = Body(...)):
    config = data.get("config") or {}
    prompt = data.get("test_prompt") or "Hello"
    started = time.perf_counter()
    try:
        params = config.get("params") or {}
        connector_config = params.get("connector_config") or {}
        transport = str(connector_config.get("transport") or "http").lower()
        if transport not in {"http", "sse", "websocket"}:
            raise ValueError("Transport must be http, sse, or websocket.")
        request_config = _request_config_for_transport(connector_config, transport)
        url = str(config.get("uri") or "")
        if not url:
            raise ValueError("Request URL is required.")
        path = str(request_config.get("path") or "")
        if path:
            url = f"{url.rstrip('/')}/{path.lstrip('/')}"
        url = _apply_query_params(url, request_config.get("queryParams") or {}, str(prompt))
        _validate_connector_url(url, transport)
        body = _build_connector_body(request_config, str(prompt))
        headers = dict(request_config.get("headers") or {})
        _apply_content_type(headers, request_config, body)
        timeout_value = float(params.get("timeout") or 30)
        if timeout_value > 1000:
            timeout_value /= 1000
        timeout = max(1, min(120, timeout_value))
        if transport == "websocket":
            method = "WEBSOCKET"
            raw = asyncio.run(_send_websocket_once(url, headers, body.decode("utf-8") if body is not None else ""))
            status_code = 101
            response_content_type = ""
            detected_transport = "websocket"
        else:
            method = request_config.get("method") or ("GET" if body is None else "POST")
            req = urllib_request.Request(url, data=body, headers=headers, method=method)
            with open_with_current_network_settings(req, timeout) as response:
                response_content_type = _response_content_type(response)
                detected_transport = _detect_connector_transport(
                    transport,
                    response_content_type,
                )
                raw = _read_connector_response_body(response, detected_transport)
                detected_transport = _detect_connector_transport(
                    transport,
                    response_content_type,
                    raw,
                )
                status_code = response.status
        extracted = _extract_connector_response(raw, connector_config.get("response") or {})
        return {
            "status": "success",
            "duration": round((time.perf_counter() - started) * 1000),
            "requestPreview": json.dumps(
                {
                    "url": url,
                    "method": method,
                    "headers": _mask_headers(headers),
                    "body": body.decode("utf-8") if body is not None else None,
                },
                indent=2,
            ),
            "rawResponse": raw,
            "extractedResponse": extracted,
            "httpStatus": status_code,
            "responseContentType": response_content_type,
            "detectedTransport": detected_transport,
        }
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        return {"status": "error", "duration": round((time.perf_counter() - started) * 1000), "requestPreview": json.dumps({"url": config.get("uri"), "error": "HTTP error"}, indent=2), "rawResponse": raw, "extractedResponse": "", "error": f"HTTP {exc.code}: {exc.reason}"}
    except (URLError, ValueError, TimeoutError) as exc:
        return {"status": "error", "duration": round((time.perf_counter() - started) * 1000), "requestPreview": json.dumps({"url": config.get("uri")}, indent=2), "rawResponse": "", "extractedResponse": "", "error": str(exc)}
    except Exception as exc:
        return {"status": "error", "duration": round((time.perf_counter() - started) * 1000), "requestPreview": json.dumps({"url": config.get("uri")}, indent=2), "rawResponse": "", "extractedResponse": "", "error": str(exc)}


@router.post("/connectors/ai-configure", summary="Generate and verify a configurable connector with the active AI model")
def ai_configure_connector(data: dict[str, Any] = Body(...)) -> dict[str, Any]:
    request_information = str(data.get("request_information") or "").strip()
    partial_config: dict[str, Any] | None = None
    test_prompt = "Hello"
    ai_service: ConnectorAIService | None = None
    current_stage = "analysis"
    try:
        ai_service = ConnectorAIService()
        draft = ai_service.generate_draft(request_information)
        partial_config = draft["config"]
        test_prompt = str(draft.get("testPrompt") or "Hello")
        missing = list(draft.get("missingInformation") or [])
        if missing:
            return {
                "status": "partial",
                "stage": "analysis",
                "message": "AI filled the fields it could, but more request information is required.",
                "missingInformation": missing,
                "config": partial_config,
                "testPrompt": test_prompt,
                "provider": ai_service.provider,
                "model": ai_service.model,
            }

        current_stage = "request"
        test_result = test_connector({"config": partial_config, "test_prompt": test_prompt})
        if test_result.get("status") != "success":
            reason = str(test_result.get("error") or "The target request failed.")
            return {
                "status": "partial",
                "stage": "request",
                "message": f"The generated request could not be completed: {reason}",
                "missingInformation": _request_failure_suggestions(reason),
                "config": partial_config,
                "testPrompt": test_prompt,
                "testResult": test_result,
                "provider": ai_service.provider,
                "model": ai_service.model,
            }

        raw_response = str(test_result.get("rawResponse") or "")
        current_stage = "response"
        try:
            response_mapping = ai_service.infer_response(
                raw_response=raw_response,
                extracted_hint=str(test_result.get("extractedResponse") or ""),
            )
        except Exception as error:
            if not isinstance(error, ConnectorAIError):
                logger.exception("Connector AI response-field inference failed")
            return {
                "status": "partial",
                "stage": "response",
                "message": (
                    str(error)
                    if isinstance(error, ConnectorAIError)
                    else (
                        "The request succeeded, but the response field could not be "
                        "identified automatically."
                    )
                ),
                "missingInformation": [
                    "Provide a representative successful response body or identify the field that contains the assistant answer."
                ],
                "config": partial_config,
                "testPrompt": test_prompt,
                "testResult": test_result,
                "provider": ai_service.provider,
                "model": ai_service.model,
            }

        try:
            partial_config["params"]["connector_config"]["response"] = response_mapping
            extracted = _extract_connector_response(raw_response, response_mapping)
        except Exception:
            logger.exception("Connector AI response mapping could not be applied")
            return {
                "status": "partial",
                "stage": "response",
                "message": (
                    "The request succeeded, but the proposed response mapping was not "
                    "valid for the returned data."
                ),
                "missingInformation": [
                    "Select the exact response value in Output Mapping to finish the connector."
                ],
                "config": partial_config,
                "testPrompt": test_prompt,
                "testResult": test_result,
                "provider": ai_service.provider,
                "model": ai_service.model,
            }
        test_result["extractedResponse"] = extracted
        if extracted and not response_mapping.get("selectedText"):
            response_mapping["selectedText"] = extracted
        if not extracted:
            return {
                "status": "partial",
                "stage": "response",
                "message": "The request succeeded, but AI could not verify the assistant answer field in the response.",
                "missingInformation": [
                    "Provide a representative successful response body or identify the exact response field that contains the assistant answer."
                ],
                "config": partial_config,
                "testPrompt": test_prompt,
                "testResult": test_result,
                "provider": ai_service.provider,
                "model": ai_service.model,
            }

        return {
            "status": "completed",
            "stage": "completed",
            "message": "AI generated, requested, and verified the connector configuration.",
            "missingInformation": [],
            "config": partial_config,
            "testPrompt": test_prompt,
            "testResult": test_result,
            "provider": ai_service.provider,
            "model": ai_service.model,
        }
    except ConnectorAIError as error:
        return {
            "status": "error",
            "stage": "analysis",
            "message": str(error),
            "missingInformation": [],
            "config": partial_config,
            "testPrompt": test_prompt,
            "provider": ai_service.provider if ai_service else "",
            "model": ai_service.model if ai_service else "",
        }
    except Exception:
        logger.exception("Connector AI configuration failed during %s", current_stage)
        stage_messages = {
            "request": (
                "The request configuration was generated, but the target request could "
                "not be completed."
            ),
            "response": (
                "The target responded, but its answer field could not be configured "
                "automatically."
            ),
        }
        return {
            "status": "error",
            "stage": current_stage,
            "message": stage_messages.get(
                current_stage,
                "The request information could not be analyzed. Existing fields were kept.",
            ),
            "missingInformation": [
                "Review the generated fields and provide a representative successful "
                "response sample if response mapping is still needed."
            ],
            "config": partial_config,
            "testPrompt": test_prompt,
            "provider": ai_service.provider if ai_service else "",
            "model": ai_service.model if ai_service else "",
        }


def _request_failure_suggestions(reason: str) -> list[str]:
    lowered = reason.lower()
    suggestions: list[str] = []
    if "401" in lowered or "403" in lowered or "unauthorized" in lowered or "forbidden" in lowered:
        suggestions.append("Provide a valid Bearer token, API key, Cookie, or Basic Auth credential.")
    if "404" in lowered or "not found" in lowered:
        suggestions.append("Confirm the complete request URL and path.")
    if "timed out" in lowered or "timeout" in lowered:
        suggestions.append("Confirm the service is reachable and provide an appropriate timeout.")
    if "name or service" in lowered or "getaddrinfo" in lowered or "refused" in lowered:
        suggestions.append("Confirm the host is reachable from this machine.")
    if not suggestions:
        suggestions.append("Provide a complete cURL example, required credentials, and any mandatory headers or query parameters.")
    return suggestions


def _extract_connector_response(raw: str, response_config: dict[str, Any]) -> str:
    response_type = response_config.get("type")
    if response_type == "text":
        return raw
    if response_type == "text-fragment":
        inferred_path = _json_path_from_output_sample(
            str(response_config.get("sampleResponse") or "")
        )
        if inferred_path:
            response_config = {**response_config, "type": "json-path", "path": inferred_path}
        else:
            extracted = _extract_text_fragment(raw, response_config)
            return extracted if extracted is not None else raw
    # A saved JSON path is more specific than the legacy event-data type.
    # Prefer it so each SSE payload is decoded before its answer is joined.
    if response_type == "event-data" and not response_config.get("path"):
        payloads = _event_payloads(raw)
        return "".join(payloads) if payloads else raw
    event_payloads = _event_payloads(raw)
    json_documents = _json_documents(raw)
    for path in (response_config.get("path"), response_config.get("fallbackPath")):
        if not path:
            continue
        streamed_values: list[str] = []
        for payload in event_payloads:
            try:
                value = _read_json_path(json.loads(payload), path)
            except (TypeError, ValueError):
                continue
            if value is not None:
                streamed_values.append(str(value))
        if streamed_values:
            return "".join(streamed_values)
        for parsed in reversed(json_documents):
            value = _read_json_path(parsed, path)
            if value is not None:
                return _stringify_extracted_value(value)
    return raw if not json_documents else ""


def _extract_text_fragment(raw: str, response_config: dict[str, Any]) -> str | None:
    prefix = str(response_config.get("prefix") or "")
    suffix = str(response_config.get("suffix") or "")
    if prefix and prefix in raw:
        start = raw.find(prefix) + len(prefix)
        if suffix:
            end = raw.find(suffix, start)
            if end >= 0:
                return raw[start:end]
        return raw[start:]
    selected = str(response_config.get("selectedText") or "")
    if selected and selected in raw:
        return selected
    return None


def _read_json_path(data: Any, path: str) -> Any:
    current = data
    if path.strip() in {"", "$"}:
        return current
    for part in path.replace("$.", "").split("."):
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            index = int(part)
            if index >= len(current):
                return None
            current = current[index]
        else:
            return None
    return current


def _parse_json_or_event_payload(raw: str) -> Any | None:
    documents = _json_documents(raw)
    if documents:
        return documents[-1]
    for payload in _event_payloads(raw):
        try:
            return json.loads(payload)
        except Exception:
            continue
    return None


def _json_documents(raw: str) -> list[Any]:
    decoder = json.JSONDecoder()
    documents: list[Any] = []
    cursor = 0
    while cursor < len(raw):
        while cursor < len(raw) and raw[cursor].isspace():
            cursor += 1
        if cursor >= len(raw):
            break
        try:
            value, end = decoder.raw_decode(raw, cursor)
        except (TypeError, ValueError):
            return []
        documents.append(value)
        cursor = end
    return documents


def _stringify_extracted_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _json_path_from_output_sample(sample: str) -> str | None:
    def walk(value: Any, path: str = "$") -> str | None:
        if isinstance(value, dict):
            for key, child in value.items():
                found = walk(child, f"{path}.{key}")
                if found:
                    return found
        elif isinstance(value, list):
            for index, child in enumerate(value):
                found = walk(child, f"{path}.{index}")
                if found:
                    return found
        elif "{{ output }}" in str(value):
            return path
        return None

    for document in reversed(_json_documents(sample)):
        found = walk(document)
        if found:
            return found
    return None


def _event_payloads(raw: str) -> list[str]:
    return [
        line.replace("data:", "", 1).strip()
        for line in raw.splitlines()
        if line.startswith("data:")
        and line.replace("data:", "", 1).strip()
        and line.replace("data:", "", 1).strip() != "[DONE]"
    ]


def _mask_headers(headers: dict[str, Any]) -> dict[str, Any]:
    return {key: ("***" if key.lower() in {"authorization", "cookie", "x-api-key"} else value) for key, value in headers.items()}


def _request_config_for_transport(connector_config: dict[str, Any], transport: str) -> dict[str, Any]:
    key = {"http": "request", "sse": "stream", "websocket": "websocket"}[transport]
    return dict(connector_config.get(key) or {})


def _validate_connector_url(url: str, transport: str) -> None:
    scheme = urlsplit(url).scheme.lower()
    allowed = {"ws", "wss"} if transport == "websocket" else {"http", "https"}
    if scheme not in allowed:
        expected = "ws:// or wss://" if transport == "websocket" else "http:// or https://"
        raise ValueError(f"Request URL must start with {expected} for {transport.upper()}.")


def _apply_content_type(headers: dict[str, Any], request_config: dict[str, Any], body: bytes | None) -> None:
    if body is None:
        return
    body_type = request_config.get("bodyType") or "json"
    if body_type == "multipart":
        _set_header_case_insensitive(
            headers,
            "content-type",
            f"multipart/form-data; boundary={_multipart_boundary(request_config)}",
        )
        return
    content_type = {
        "form": "application/x-www-form-urlencoded",
        "raw": "text/plain; charset=utf-8",
        "json": "application/json",
    }.get(body_type)
    if content_type:
        headers.setdefault("content-type", content_type)


def _apply_query_params(url: str, params: dict[str, Any], prompt: str) -> str:
    if not params:
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    for key, value in params.items():
        query[str(key)] = str(value).replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _build_connector_body(request_config: dict[str, Any], prompt: str) -> bytes | None:
    body_type = request_config.get("bodyType") or "json"
    if body_type == "none":
        return None
    if body_type == "form":
        fields = {
            str(key): str(value).replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt)
            for key, value in (request_config.get("formFields") or {}).items()
        }
        return urlencode(fields).encode("utf-8")
    if body_type == "multipart":
        return _build_multipart_body(request_config, prompt)
    body_template = (
        request_config.get("bodyTemplate")
        or request_config.get("messageTemplate")
        or '{"prompt":"{{ prompt }}"}'
    )
    replacement = json.dumps(prompt, ensure_ascii=False)[1:-1] if body_type == "json" else prompt
    return body_template.replace("{{ prompt }}", replacement).replace("{{prompt}}", replacement).encode("utf-8")


def _multipart_boundary(request_config: dict[str, Any]) -> str:
    fields = request_config.get("formFields") or {}
    fingerprint = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"----OxoTrackerBoundary{hashlib.sha256(fingerprint).hexdigest()[:24]}"


def _build_multipart_body(request_config: dict[str, Any], prompt: str) -> bytes:
    boundary = _multipart_boundary(request_config)
    chunks: list[bytes] = []
    for raw_name, raw_value in (request_config.get("formFields") or {}).items():
        name = str(raw_name).replace("\r", "").replace("\n", "").replace('"', "\\\"")
        value = str(raw_value).replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt)
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("ascii"),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks)


def _set_header_case_insensitive(headers: dict[str, Any], name: str, value: str) -> None:
    existing = next((key for key in headers if str(key).lower() == name.lower()), None)
    if existing is None:
        headers[name] = value
    else:
        headers[existing] = value


def _read_connector_response_body(response: Any, transport: str) -> str:
    if transport != "sse":
        return response.read().decode("utf-8")
    lines: list[str] = []
    total_bytes = 0
    for _ in range(512):
        try:
            line = response.readline()
        except (TimeoutError, OSError):
            break
        if not line:
            break
        total_bytes += len(line)
        if total_bytes > 1_048_576:
            break
        decoded = line.decode("utf-8", errors="replace")
        lines.append(decoded)
        if decoded.strip() == "data: [DONE]":
            break
    return "".join(lines)


def _response_content_type(response: Any) -> str:
    headers = getattr(response, "headers", None)
    if headers is None:
        return ""
    try:
        return str(headers.get("Content-Type") or "").strip()
    except (AttributeError, TypeError):
        return ""


def _detect_connector_transport(
    configured_transport: str,
    content_type: str = "",
    raw_response: str = "",
) -> str:
    if configured_transport == "websocket":
        return "websocket"
    normalized_content_type = content_type.lower()
    if "text/event-stream" in normalized_content_type:
        return "sse"
    if raw_response and any(
        line.startswith(("data:", "event:", "id:", "retry:"))
        for line in raw_response.lstrip("\ufeff").splitlines()
    ):
        return "sse"
    if raw_response and configured_transport == "sse":
        return "http"
    return configured_transport


async def _send_websocket_once(url: str, headers: dict[str, Any], message: str) -> str:
    try:
        import websockets
    except Exception as exc:
        raise RuntimeError("WebSocket testing requires the 'websockets' package.") from exc
    async with websockets.connect(url, extra_headers=headers or None) as websocket:
        if message:
            await websocket.send(message)
        response = await websocket.recv()
        return response if isinstance(response, str) else response.decode("utf-8", errors="replace")


@router.post("/endpoints", summary="Create model endpoint")
def create_endpoint(data: dict[str, Any] = Body(...)):
    """创建模型或应用端点，body 字段对应 Moonshot 的 api_create_endpoint 参数。"""
    return handle_call(lambda: service().create_endpoint(data))


@router.delete("/endpoints/{ep_id}", summary="删除模型端点")
def delete_endpoint(ep_id: str):
    """根据端点 ID 删除模型端点。"""
    return handle_call(lambda: service().delete_endpoint(ep_id))


@router.get("/endpoints", summary="获取全部模型端点")
def get_all_endpoint():
    """获取全部已配置模型端点详情。"""
    return handle_call(lambda: service().get_all_endpoint())


@router.get("/endpoints/names", summary="获取全部模型端点名称")
def get_all_endpoint_name():
    """获取全部已配置模型端点 ID 列表。"""
    return handle_call(lambda: service().get_all_endpoint_name())


@router.get("/endpoints/{ep_id}", summary="读取模型端点")
def read_endpoint(ep_id: str):
    """根据端点 ID 读取端点详情。"""
    return handle_call(lambda: service().read_endpoint(ep_id))


@router.patch("/endpoints/{ep_id}", summary="更新模型端点")
def update_endpoint(ep_id: str, data: dict[str, Any] = Body(...)):
    """根据端点 ID 更新端点配置。"""
    return handle_call(lambda: service().update_endpoint(ep_id, data))


# 上下文策略
@router.delete("/context-strategies/{cs_id}", summary="删除上下文策略")
def delete_context_strategy(cs_id: str):
    """根据上下文策略 ID 删除策略。"""
    return handle_call(lambda: service().delete_context_strategy(cs_id))


@router.get("/context-strategies", summary="获取全部上下文策略")
def get_all_context_strategies():
    """获取全部 red teaming 上下文策略名称。"""
    return handle_call(lambda: service().get_all_context_strategies())


@router.get("/context-strategies/metadata", summary="获取上下文策略元数据")
def get_all_context_strategy_metadata():
    """获取全部上下文策略元数据。"""
    return handle_call(lambda: service().get_all_context_strategy_metadata())


# Cookbook
@router.post("/cookbooks", summary="创建 Cookbook")
def create_cookbook(
    name: str = Body(...),
    description: str = Body(""),
    recipes: list[str] = Body(...),
):
    """创建 cookbook，用于组合多个 recipe。"""
    return handle_call(lambda: service().create_cookbook(name, description, recipes))


@router.delete("/cookbooks/{cb_id}", summary="删除 Cookbook")
def delete_cookbook(cb_id: str):
    """根据 cookbook ID 删除 cookbook。"""
    return handle_call(lambda: service().delete_cookbook(cb_id))


@router.get("/cookbooks", summary="获取全部 Cookbook")
def get_all_cookbook():
    """获取全部 cookbook 详情。"""
    return handle_call(lambda: service().get_all_cookbook())


@router.get("/cookbooks/names", summary="获取全部 Cookbook 名称")
def get_all_cookbook_name():
    """获取全部 cookbook ID 列表。"""
    return handle_call(lambda: service().get_all_cookbook_name())


@router.get("/cookbooks/{cb_id}", summary="读取 Cookbook")
def read_cookbook(cb_id: str):
    """根据 cookbook ID 读取详情。"""
    return handle_call(lambda: service().read_cookbook(cb_id))


@router.post("/cookbooks/read-batch", summary="批量读取 Cookbook")
def read_cookbooks(cb_ids: list[str] = Body(..., embed=True)):
    """根据 cookbook ID 列表批量读取详情。"""
    return handle_call(lambda: service().read_cookbooks(cb_ids))


@router.patch("/cookbooks/{cb_id}", summary="更新 Cookbook")
def update_cookbook(cb_id: str, data: dict[str, Any] = Body(...)):
    """根据 cookbook ID 更新字段。"""
    return handle_call(lambda: service().update_cookbook(cb_id, data))


# 数据集
@router.post("/datasets/convert", summary="转换数据集")
def convert_dataset(data: dict[str, Any] = Body(...)):
    """将 CSV 数据集转换为 Moonshot 数据集。"""
    return handle_call(lambda: service().convert_dataset(data))


@router.post("/datasets/download", summary="下载数据集")
def download_dataset(data: dict[str, Any] = Body(...)):
    """下载外部数据集并创建 Moonshot 数据集。"""
    return handle_call(lambda: service().download_dataset(data))


@router.post("/datasets/read", summary="读取 Dataset")
def read_dataset_post(data: dict[str, Any] = Body(...)):
    ds_id = str(data.get("ds_id") or data.get("id") or "")
    limit = int(data.get("limit") or 25)
    offset = int(data.get("offset") or 0)
    return handle_call(lambda: service().read_dataset(ds_id, limit, offset))


@router.delete("/datasets/{ds_id}", summary="删除数据集")
def delete_dataset(ds_id: str):
    """根据数据集 ID 删除数据集。"""
    return handle_call(lambda: service().delete_dataset(ds_id))


@router.post("/datasets", summary="创建 Dataset")
def create_dataset(data: dict[str, Any] = Body(...)):
    return handle_call(lambda: service().create_dataset(data))


@router.get("/datasets", summary="获取全部数据集")
def get_all_datasets():
    """获取全部数据集详情。"""
    return handle_call(lambda: service().get_all_datasets())


@router.get("/datasets/names", summary="获取全部数据集名称")
def get_all_datasets_name():
    """获取全部数据集 ID 列表。"""
    return handle_call(lambda: service().get_all_datasets_name())


@router.get("/datasets/{ds_id}", summary="读取 Dataset")
def read_dataset(ds_id: str, limit: int = 25, offset: int = 0):
    return handle_call(lambda: service().read_dataset(ds_id, limit, offset))


@router.patch("/datasets/{ds_id}", summary="更新 Dataset")
def update_dataset(ds_id: str, data: dict[str, Any] = Body(...)):
    return handle_call(lambda: service().update_dataset(ds_id, data))


# 环境变量
@router.post("/environment", summary="设置 Moonshot 环境变量")
def set_environment_variables(env_vars: dict[str, Any] = Body(..., embed=True)):
    """设置 Moonshot 资源目录映射，通常启动时已自动完成。"""
    return handle_call(lambda: service().set_environment_variables(env_vars))


# 指标
@router.delete("/metrics/{met_id}", summary="删除评估指标")
def delete_metric(met_id: str):
    """根据 metric ID 删除评估指标。"""
    return handle_call(lambda: service().delete_metric(met_id))


@router.get("/metrics", summary="获取全部评估指标")
def get_all_metric():
    """获取全部评估指标详情。"""
    return handle_call(lambda: service().get_all_metric())


@router.get("/metrics/names", summary="获取全部评估指标名称")
def get_all_metric_name():
    """获取全部评估指标 ID 列表。"""
    return handle_call(lambda: service().get_all_metric_name())


# Prompt 模板
@router.get("/prompt-templates", summary="获取 Prompt 模板详情")
def get_all_prompt_template_detail():
    """获取全部 Prompt 模板详情。"""
    return handle_call(lambda: service().get_all_prompt_template_detail())


@router.get("/prompt-templates/names", summary="获取 Prompt 模板名称")
def get_all_prompt_template_name():
    """获取全部 Prompt 模板 ID 列表。"""
    return handle_call(lambda: service().get_all_prompt_template_name())


@router.post("/prompt-templates", summary="Create Prompt Template")
def create_prompt_template(data: dict[str, Any] = Body(...)):
    """Create an Oxo-owned prompt template."""
    return handle_call(lambda: service().create_prompt_template(data))


@router.patch("/prompt-templates/{pt_id}", summary="Update Prompt Template")
def update_prompt_template_record(pt_id: str, data: dict[str, Any] = Body(...)):
    """Update an Oxo-owned prompt template without changing its ID."""
    return handle_call(lambda: service().update_prompt_template_record(pt_id, data))


@router.delete("/prompt-templates/{pt_id}", summary="删除 Prompt 模板")
def delete_prompt_template(pt_id: str):
    """根据 Prompt 模板 ID 删除模板。"""
    return handle_call(lambda: service().delete_prompt_template(pt_id))


# Recipe
@router.post("/recipes", summary="创建 Recipe")
def create_recipe(data: dict[str, Any] = Body(...)):
    """创建 benchmark recipe。"""
    return handle_call(lambda: service().create_recipe(data))


@router.delete("/recipes/{rec_id}", summary="删除 Recipe")
def delete_recipe(rec_id: str):
    """根据 recipe ID 删除 recipe。"""
    return handle_call(lambda: service().delete_recipe(rec_id))


@router.get("/recipes", summary="获取全部 Recipe")
def get_all_recipe():
    """获取全部 recipe 详情。"""
    return handle_call(lambda: service().get_all_recipe())


@router.get("/recipes/names", summary="获取全部 Recipe 名称")
def get_all_recipe_name():
    """获取全部 recipe ID 列表。"""
    return handle_call(lambda: service().get_all_recipe_name())


@router.get("/recipes/{rec_id}", summary="读取 Recipe")
def read_recipe(rec_id: str):
    """根据 recipe ID 读取 recipe 详情。"""
    return handle_call(lambda: service().read_recipe(rec_id))


@router.post("/recipes/read-batch", summary="批量读取 Recipe")
def read_recipes(rec_ids: list[str] = Body(..., embed=True)):
    """根据 recipe ID 列表批量读取 recipe 详情。"""
    return handle_call(lambda: service().read_recipes(rec_ids))


@router.patch("/recipes/{rec_id}", summary="更新 Recipe")
def update_recipe(rec_id: str, data: dict[str, Any] = Body(...)):
    """根据 recipe ID 更新 recipe。"""
    return handle_call(lambda: service().update_recipe(rec_id, data))


# 攻击模块
@router.get("/attack-modules/metadata", summary="获取攻击模块元数据")
def get_all_attack_module_metadata():
    """获取全部 red teaming 攻击模块元数据。"""
    return handle_call(lambda: service().get_all_attack_module_metadata())


@router.get("/attack-modules", summary="获取全部攻击模块")
def get_all_attack_modules():
    """获取全部 red teaming 攻击模块名称。"""
    return handle_call(lambda: service().get_all_attack_modules())


@router.delete("/attack-modules/{am_id}", summary="删除攻击模块")
def delete_attack_module(am_id: str):
    """根据攻击模块 ID 删除攻击模块。"""
    return handle_call(lambda: service().delete_attack_module(am_id))


# 结果
@router.delete("/results/{res_id}", summary="删除测试结果")
def delete_result(res_id: str):
    """根据结果 ID 删除测试结果。"""
    return handle_call(lambda: service().delete_result(res_id))


@router.get("/results", summary="获取全部测试结果")
def get_all_result():
    """获取全部测试结果摘要。"""
    return handle_call(lambda: service().get_all_result())


@router.get("/results/names", summary="获取全部测试结果名称")
def get_all_result_name():
    """获取全部测试结果 ID 列表。"""
    return handle_call(lambda: service().get_all_result_name())


@router.get("/results/{res_id}", summary="读取测试结果")
def read_result(res_id: str):
    """根据结果 ID 读取测试结果详情。"""
    return handle_call(lambda: service().read_result(res_id))


@router.post("/results/read-batch", summary="批量读取测试结果")
def read_results(res_ids: list[str] = Body(..., embed=True)):
    """根据结果 ID 列表批量读取测试结果。"""
    return handle_call(lambda: service().read_results(res_ids))


# Run / Runner
@router.get("/runs", summary="获取运行记录")
def get_all_run(runner_id: str = ""):
    """根据 runner ID 获取运行记录。"""
    return handle_call(lambda: service().get_all_run(runner_id))


@router.post("/runners", summary="创建 Runner")
def create_runner(
    name: str = Body(...),
    endpoints: list[str] = Body(...),
    description: str = Body(""),
):
    """创建 runner，并绑定一组模型端点。"""
    return handle_call(lambda: service().create_runner(name, endpoints, description))


@router.delete("/runners/{runner_id}", summary="删除 Runner")
def delete_runner(runner_id: str):
    """根据 runner ID 删除 runner。"""
    return handle_call(lambda: service().delete_runner(runner_id))


@router.get("/runners", summary="获取全部 Runner")
def get_all_runner():
    """获取全部 runner 详情。"""
    return handle_call(lambda: service().get_all_runner())


@router.get("/runners/names", summary="获取全部 Runner 名称")
def get_all_runner_name():
    """获取全部 runner ID 列表。"""
    return handle_call(lambda: service().get_all_runner_name())


@router.get("/runners/{runner_id}/load", summary="加载 Runner")
def load_runner(runner_id: str):
    """根据 runner ID 加载 runner。"""
    return handle_call(lambda: service().load_runner(runner_id))


@router.get("/runners/{runner_id}", summary="读取 Runner")
def read_runner(runner_id: str):
    """根据 runner ID 读取 runner 配置。"""
    return handle_call(lambda: service().read_runner(runner_id))


# Session
@router.post("/sessions", summary="创建红队 Session")
def create_session(
    runner_id: str = Body(...),
    database_instance: Any = Body(...),
    endpoints: list[str] = Body(...),
    runner_args: dict[str, Any] = Body(...),
):
    """创建 red teaming session；通常建议后续封装成更高层业务接口。"""
    return handle_call(
        lambda: service().create_session(runner_id, database_instance, endpoints, runner_args)
    )


@router.post("/redteam/sessions", summary="Create Red Team Session")
def create_redteam_session(data: dict[str, Any] = Body(...)):
    """Create a runner-backed red-team session with endpoint and utility configuration."""
    return handle_call(
        lambda: service().create_redteam_session(
            name=data.get("name", ""),
            endpoints=data.get("endpoints", []),
            description=data.get("description", ""),
            runner_args=data.get("runner_args", {}),
        )
    )


@router.post("/redteam/prepare-prompt", summary="Prepare Red Team Prompt")
def prepare_redteam_prompt(data: dict[str, Any] = Body(...)):
    """Prepare the final prompt after applying Payload and Attack Module selections."""
    return handle_call(
        lambda: service().prepare_redteam_prompt(
            prompt=str(data.get("prompt", "")),
            prompt_template=str(data.get("prompt_template", "")),
            attack_module=str(data.get("attack_module", "")),
        )
    )


@router.post("/redteam/sessions/{runner_id}/prompt", summary="Send Red Team Prompt")
async def send_redteam_prompt(runner_id: str, data: dict[str, Any] = Body(...)):
    """Send one manual red-team prompt to a Moonshot session."""
    try:
        return await service().send_redteam_prompt(
            runner_id,
            str(data.get("user_prompt", "")),
            str(data.get("prepared_prompt", "")),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/sessions/{runner_id}", summary="删除红队 Session")
def delete_session(runner_id: str):
    """根据 runner ID 删除 red teaming session。"""
    return handle_call(lambda: service().delete_session(runner_id))


@router.delete(
    "/redteam/sessions/{runner_id}",
    summary="Delete a temporary runner-backed Red Team Session",
)
def delete_redteam_session(runner_id: str):
    return handle_call(lambda: service().delete_redteam_session(runner_id))


@router.get("/sessions/{runner_id}/chats", summary="获取 Session 聊天记录")
def get_all_chats_from_session(runner_id: str):
    """根据 runner ID 获取 session 聊天记录。"""
    return handle_call(lambda: service().get_all_chats_from_session(runner_id))


@router.get("/sessions/metadata", summary="获取全部 Session 元数据")
def get_all_session_metadata():
    """获取全部 red teaming session 元数据。"""
    return handle_call(lambda: service().get_all_session_metadata())


@router.get("/sessions/names", summary="获取全部 Session 名称")
def get_all_session_names():
    """获取全部 red teaming session 名称。"""
    return handle_call(lambda: service().get_all_session_names())


@router.get("/sessions/available", summary="获取可用 Session 信息")
def get_available_session_info():
    """获取可用 session ID 和元数据。"""
    return handle_call(lambda: service().get_available_session_info())


@router.get("/sessions/{runner_id}", summary="加载 Session")
def load_session(runner_id: str):
    """根据 runner ID 加载 session。"""
    return handle_call(lambda: service().load_session(runner_id))


@router.patch("/sessions/{runner_id}/attack-module", summary="更新 Session 攻击模块")
def update_attack_module(runner_id: str, attack_module_id: str = Body(..., embed=True)):
    """更新 session 使用的攻击模块。"""
    return handle_call(lambda: service().update_attack_module(runner_id, attack_module_id))


@router.patch("/sessions/{runner_id}/context-strategy", summary="更新 Session 上下文策略")
def update_context_strategy(runner_id: str, context_strategy: str = Body(..., embed=True)):
    """更新 session 使用的上下文策略。"""
    return handle_call(lambda: service().update_context_strategy(runner_id, context_strategy))


@router.patch("/sessions/{runner_id}/context-strategy/previous-prompts", summary="更新上下文历史轮数")
def update_cs_num_of_prev_prompts(
    runner_id: str,
    num_of_prev_prompts: int = Body(..., embed=True),
):
    """更新上下文策略使用的历史 prompt 数量。"""
    return handle_call(
        lambda: service().update_cs_num_of_prev_prompts(runner_id, num_of_prev_prompts)
    )


@router.patch("/sessions/{runner_id}/metric", summary="更新 Session 指标")
def update_metric(runner_id: str, metric_id: str = Body(..., embed=True)):
    """更新 session 使用的指标。"""
    return handle_call(lambda: service().update_metric(runner_id, metric_id))


@router.patch("/sessions/{runner_id}/prompt-template", summary="更新 Session Prompt 模板")
def update_prompt_template(runner_id: str, prompt_template: str = Body(..., embed=True)):
    """更新 session 使用的 Prompt 模板。"""
    return handle_call(lambda: service().update_prompt_template(runner_id, prompt_template))


@router.patch("/sessions/{runner_id}/system-prompt", summary="更新 Session 系统提示词")
def update_system_prompt(runner_id: str, system_prompt: str = Body(..., embed=True)):
    """更新 session 使用的系统提示词。"""
    return handle_call(lambda: service().update_system_prompt(runner_id, system_prompt))


# Bookmark
@router.get("/bookmarks", summary="获取全部书签")
def get_all_bookmarks():
    """获取全部 bookmark。"""
    return handle_call(lambda: service().get_all_bookmarks())


@router.get("/bookmarks/{bookmark_name}", summary="读取书签")
def get_bookmark(bookmark_name: str):
    """根据 bookmark 名称读取书签。"""
    return handle_call(lambda: service().get_bookmark(bookmark_name))


@router.post("/bookmarks", summary="新增书签")
def insert_bookmark(data: dict[str, Any] = Body(...)):
    """新增 red teaming bookmark。"""
    return handle_call(lambda: service().insert_bookmark(data))


@router.delete("/bookmarks/{bookmark_name}", summary="删除书签")
def delete_bookmark(bookmark_name: str):
    """根据 bookmark 名称删除书签。"""
    return handle_call(lambda: service().delete_bookmark(bookmark_name))


@router.delete("/bookmarks", summary="删除全部书签")
def delete_all_bookmark():
    """删除全部 bookmark。"""
    return handle_call(lambda: service().delete_all_bookmark())


@router.post("/bookmarks/export", summary="导出书签")
def export_bookmarks(export_file_name: str = Body("bookmarks", embed=True)):
    """导出 bookmark 文件。"""
    return handle_call(lambda: service().export_bookmarks(export_file_name))
