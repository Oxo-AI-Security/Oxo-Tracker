import base64
import hashlib
import ipaddress
import json
import socket
from urllib import request
from urllib.parse import urlencode, urlsplit, urlunsplit, parse_qsl

from moonshot.src.connectors.connector import Connector, perform_retry
from moonshot.src.connectors.connector_response import ConnectorResponse
from moonshot.src.connectors_endpoints.connector_endpoint_arguments import ConnectorEndpointArguments


APPROVED_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _is_declared_loopback_url(url: str) -> bool:
    return (urlsplit(url).hostname or "").rstrip(".").lower() in APPROVED_LOOPBACK_HOSTS


def _assert_verified_loopback_url(url: str) -> None:
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https", "ws", "wss"}:
        raise RuntimeError("Local test target uses an unsupported URL scheme.")
    if parts.username is not None or parts.password is not None:
        raise RuntimeError("Local test target URL must not contain user information.")
    host = (parts.hostname or "").rstrip(".").lower()
    if host not in APPROVED_LOOPBACK_HOSTS:
        raise RuntimeError("Local test target redirect left the approved loopback host set.")
    addresses = {
        item[4][0]
        for item in socket.getaddrinfo(host, parts.port, type=socket.SOCK_STREAM)
    }
    if not addresses or any(
        not ipaddress.ip_address(address.split("%", 1)[0]).is_loopback
        for address in addresses
    ):
        raise RuntimeError("Local test target DNS resolution is not exclusively loopback.")


class _LoopbackOnlyRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _assert_verified_loopback_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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
        self._apply_legacy_auth(headers)
        req = request.Request(
            url,
            data=body,
            headers=headers,
            method=request_config.get("method") or ("GET" if body is None else "POST"),
        )
        if _is_declared_loopback_url(url):
            _assert_verified_loopback_url(url)
            opener = request.build_opener(
                request.ProxyHandler({}),
                _LoopbackOnlyRedirectHandler(),
            )
        else:
            opener = request.build_opener()
        with opener.open(req, timeout=self.timeout) as response:
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
        if _is_declared_loopback_url(url):
            _assert_verified_loopback_url(url)
        message_template = request_config.get("messageTemplate") or '{"prompt":"{{ prompt }}"}'
        replacement = json.dumps(prompt, ensure_ascii=False)[1:-1]
        message = message_template.replace("{{ prompt }}", replacement).replace("{{prompt}}", replacement)
        headers = dict(request_config.get("headers") or {})
        self._apply_legacy_auth(headers)
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
        if body_type == "multipart":
            return self._build_multipart_body(request_config, prompt)
        body_template = (
            request_config.get("bodyTemplate")
            or request_config.get("messageTemplate")
            or '{"prompt":"{{ prompt }}"}'
        )
        replacement = json.dumps(prompt, ensure_ascii=False)[1:-1] if body_type == "json" else prompt
        return body_template.replace("{{ prompt }}", replacement).replace("{{prompt}}", replacement).encode(
            "utf-8"
        )

    def _multipart_boundary(self, request_config: dict) -> str:
        fields = request_config.get("formFields") or {}
        fingerprint = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return f"----OxoTrackerBoundary{hashlib.sha256(fingerprint).hexdigest()[:24]}"

    def _build_multipart_body(self, request_config: dict, prompt: str) -> bytes:
        boundary = self._multipart_boundary(request_config)
        chunks = []
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

    def _apply_legacy_auth(self, headers: dict) -> None:
        # Compatibility for endpoints saved before credentials became ordinary request headers.
        auth = self.config.get("auth") or {}
        auth_type = str(auth.get("type") or "none")
        header_name = auth.get("headerName") or (
            "x-api-key" if auth_type == "api-key" else "Cookie" if auth_type == "cookie" else "Authorization"
        )
        if any(str(name).lower() == str(header_name).lower() for name in headers):
            return
        if auth_type == "bearer" and self.token:
            headers[header_name] = f"Bearer {self.token}"
        elif auth_type == "api-key" and self.token:
            headers[header_name] = self.token
        elif auth_type == "cookie" and self.token:
            headers[header_name] = self.token
        elif auth_type == "basic":
            username = str(auth.get("username") or "")
            if username or self.token:
                encoded = base64.b64encode(f"{username}:{self.token}".encode("utf-8")).decode("ascii")
                headers["Authorization"] = f"Basic {encoded}"

    def _apply_content_type(self, headers: dict, request_config: dict, body) -> None:
        if body is None:
            return
        body_type = request_config.get("bodyType") or "json"
        if body_type == "multipart":
            self._set_header_case_insensitive(
                headers,
                "content-type",
                f"multipart/form-data; boundary={self._multipart_boundary(request_config)}",
            )
            return
        content_type = {
            "form": "application/x-www-form-urlencoded",
            "raw": "text/plain; charset=utf-8",
            "json": "application/json",
        }.get(body_type)
        if content_type:
            headers.setdefault("content-type", content_type)

    def _set_header_case_insensitive(self, headers: dict, name: str, value: str) -> None:
        existing = next((key for key in headers if str(key).lower() == name.lower()), None)
        if existing is None:
            headers[name] = value
        else:
            headers[existing] = value

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
        response_type = response_config.get("type")
        if response_type == "text":
            return raw
        if response_type == "text-fragment":
            inferred_path = self._json_path_from_output_sample(
                str(response_config.get("sampleResponse") or "")
            )
            if inferred_path:
                response_config = dict(response_config, type="json-path", path=inferred_path)
            else:
                extracted = self._extract_text_fragment(raw, response_config)
                return extracted if extracted is not None else raw
        # Older endpoint records may contain both ``type: event-data`` and a
        # JSON path. A path is more specific and must win; otherwise streamed
        # JSON objects are rendered verbatim instead of their answer fragments.
        if response_type == "event-data" and not response_config.get("path"):
            payloads = self._event_payloads(raw)
            return "".join(payloads) if payloads else raw
        event_payloads = self._event_payloads(raw)
        json_documents = self._json_documents(raw)
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
            # Some HTTP APIs return a sequence of complete JSON documents in a
            # single chunked body. This is not an SSE token stream: the last
            # matching document is the final response and must be shown once.
            for data in reversed(json_documents):
                value = self._read_json_path(data, path)
                if value is not None:
                    return self._stringify_extracted_value(value)
        return raw if not json_documents else ""

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
        if str(path).strip() in {"", "$"}:
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

    def _parse_json_or_event_payload(self, raw: str):
        documents = self._json_documents(raw)
        if documents:
            return documents[-1]
        for payload in self._event_payloads(raw):
            try:
                return json.loads(payload)
            except Exception:
                continue
        return None

    def _json_documents(self, raw: str):
        decoder = json.JSONDecoder()
        documents = []
        cursor = 0
        length = len(raw)
        while cursor < length:
            while cursor < length and raw[cursor].isspace():
                cursor += 1
            if cursor >= length:
                break
            try:
                value, end = decoder.raw_decode(raw, cursor)
            except (TypeError, ValueError):
                return []
            documents.append(value)
            cursor = end
        return documents

    def _stringify_extracted_value(self, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        if value is True:
            return "true"
        if value is False:
            return "false"
        return str(value)

    def _json_path_from_output_sample(self, sample: str):
        def walk(value, path="$"):
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

        for document in reversed(self._json_documents(sample)):
            found = walk(document)
            if found:
                return found
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
