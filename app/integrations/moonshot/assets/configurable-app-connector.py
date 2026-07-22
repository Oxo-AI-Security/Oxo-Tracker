import base64
import json
from urllib import request
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from moonshot.src.connectors.connector import Connector, perform_retry
from moonshot.src.connectors.connector_response import ConnectorResponse
from moonshot.src.connectors_endpoints.connector_endpoint_arguments import ConnectorEndpointArguments


class ConfigurableAppConnector(Connector):
    def __init__(self, ep_arguments: ConnectorEndpointArguments):
        super().__init__(ep_arguments)
        self.config = self.params.get("connector_config", {})
        if self.timeout > 1000:
            self.timeout /= 1000

    @Connector.rate_limited
    @perform_retry
    async def get_response(self, prompt: str) -> ConnectorResponse:
        transport = self.config.get("transport", "http")
        if transport not in {"http", "sse", "websocket"}:
            transport = "http"
        raw = await self._send_websocket(prompt) if transport == "websocket" else self._send_http_like(prompt)
        return ConnectorResponse(response=self._extract_response(raw))

    def _send_http_like(self, prompt: str) -> str:
        request_config = self.config.get("stream") if self.config.get("transport") == "sse" else self.config.get("request")
        request_config = request_config or {}
        path = request_config.get("path", "")
        url = f"{self.endpoint.rstrip('/')}/{path.lstrip('/')}" if path else self.endpoint
        url = self._apply_query_params(url, request_config.get("queryParams") or {}, prompt)
        body = self._build_body(request_config, prompt)
        headers = dict(request_config.get("headers") or {})
        self._apply_content_type(headers, request_config, body)
        self._apply_auth(headers)
        req = request.Request(
            url,
            data=body,
            headers=headers,
            method=request_config.get("method") or ("GET" if body is None else "POST"),
        )
        with request.urlopen(req, timeout=self.timeout) as response:
            return self._read_response_body(response)

    async def _send_websocket(self, prompt: str) -> str:
        try:
            import websockets
        except Exception as exc:
            raise RuntimeError("WebSocket connector requires the 'websockets' package.") from exc
        request_config = self.config.get("websocket") or {}
        path = request_config.get("path", "")
        url = f"{self.endpoint.rstrip('/')}/{path.lstrip('/')}" if path else self.endpoint
        url = self._apply_query_params(url, request_config.get("queryParams") or {}, prompt)
        message_template = request_config.get("messageTemplate") or '{"prompt":"{{ prompt }}"}'
        replacement = json.dumps(prompt, ensure_ascii=False)[1:-1]
        message = message_template.replace("{{ prompt }}", replacement).replace("{{prompt}}", replacement)
        headers = dict(request_config.get("headers") or {})
        self._apply_auth(headers)
        async with websockets.connect(url, extra_headers=headers or None) as websocket:
            await websocket.send(message)
            response = await websocket.recv()
            return response if isinstance(response, str) else response.decode("utf-8", errors="replace")

    def _apply_query_params(self, url: str, params: dict, prompt: str) -> str:
        if not params:
            return url
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        for key, value in params.items():
            query[str(key)] = str(value).replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))

    def _build_body(self, request_config: dict, prompt: str):
        body_type = request_config.get("bodyType") or "json"
        if body_type == "none":
            return None
        if body_type == "form":
            fields = {
                str(key): str(value).replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt)
                for key, value in (request_config.get("formFields") or {}).items()
            }
            return urlencode(fields).encode("utf-8")
        body_template = (
            request_config.get("bodyTemplate")
            or request_config.get("messageTemplate")
            or '{"prompt":"{{ prompt }}"}'
        )
        replacement = json.dumps(prompt, ensure_ascii=False)[1:-1] if body_type == "json" else prompt
        return body_template.replace("{{ prompt }}", replacement).replace("{{prompt}}", replacement).encode(
            "utf-8"
        )

    def _apply_auth(self, headers: dict) -> None:
        auth = self.config.get("auth") or {}
        auth_type = str(auth.get("type") or "none")
        if auth_type == "bearer" and self.token:
            headers[auth.get("headerName") or "Authorization"] = f"Bearer {self.token}"
        elif auth_type == "api-key" and self.token:
            headers[auth.get("headerName") or "x-api-key"] = self.token
        elif auth_type == "cookie" and self.token:
            headers[auth.get("headerName") or "Cookie"] = self.token
        elif auth_type == "basic":
            username = str(auth.get("username") or "")
            if username or self.token:
                encoded = base64.b64encode(f"{username}:{self.token}".encode("utf-8")).decode("ascii")
                headers["Authorization"] = f"Basic {encoded}"

    def _apply_content_type(self, headers: dict, request_config: dict, body) -> None:
        if body is None:
            return
        body_type = request_config.get("bodyType") or "json"
        content_type = {
            "form": "application/x-www-form-urlencoded",
            "raw": "text/plain; charset=utf-8",
            "json": "application/json",
        }.get(body_type)
        if content_type:
            headers.setdefault("content-type", content_type)

    def _read_response_body(self, response) -> str:
        if self.config.get("transport") != "sse":
            return response.read().decode("utf-8")
        lines = []
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

    def _extract_response(self, raw: str) -> str:
        response_config = self.config.get("response") or {}
        if response_config.get("type") == "text":
            return raw
        if response_config.get("type") == "text-fragment":
            extracted = self._extract_text_fragment(raw, response_config)
            return extracted if extracted is not None else raw
        if response_config.get("type") == "event-data":
            payloads = self._event_payloads(raw)
            return "".join(payloads) if payloads else raw
        data = self._parse_json_or_event_payload(raw)
        event_payloads = self._event_payloads(raw)
        for path in (response_config.get("path", "$.output"), response_config.get("fallbackPath")):
            if not path:
                continue
            streamed_values = []
            for payload in event_payloads:
                try:
                    value = self._read_json_path(json.loads(payload), path)
                except (TypeError, ValueError):
                    continue
                if value is not None:
                    streamed_values.append(str(value))
            if streamed_values:
                return "".join(streamed_values)
            if data is not None:
                value = self._read_json_path(data, path)
                if value is not None:
                    return str(value)
        return raw if data is None else ""

    def _extract_text_fragment(self, raw: str, response_config: dict):
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

    def _read_json_path(self, data, path: str):
        current = data
        for part in path.replace("$.", "").split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                current = current[int(part)]
            else:
                return None
        return current

    def _parse_json_or_event_payload(self, raw: str):
        try:
            return json.loads(raw)
        except Exception:
            pass
        for payload in self._event_payloads(raw):
            try:
                return json.loads(payload)
            except Exception:
                continue
        return None

    def _event_payloads(self, raw: str):
        payloads = []
        for line in raw.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line.replace("data:", "", 1).strip()
            if payload and payload != "[DONE]":
                payloads.append(payload)
        return payloads
