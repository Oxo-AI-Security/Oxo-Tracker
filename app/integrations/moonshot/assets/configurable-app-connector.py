import json
from urllib import request

from moonshot.src.connectors.connector import Connector, perform_retry
from moonshot.src.connectors.connector_response import ConnectorResponse
from moonshot.src.connectors_endpoints.connector_endpoint_arguments import ConnectorEndpointArguments


class ConfigurableAppConnector(Connector):
    def __init__(self, ep_arguments: ConnectorEndpointArguments):
        super().__init__(ep_arguments)
        self.config = self.params.get("connector_config", {})

    @Connector.rate_limited
    @perform_retry
    async def get_response(self, prompt: str) -> ConnectorResponse:
        transport = self.config.get("transport", "http")
        if transport not in {"http", "sse", "websocket"}:
            transport = "http"
        raw = self._send_http_like(prompt)
        return ConnectorResponse(response=self._extract_response(raw))

    def _send_http_like(self, prompt: str) -> str:
        request_config = (
            self.config.get("request")
            or self.config.get("stream")
            or self.config.get("websocket")
            or {}
        )
        path = request_config.get("path", "")
        url = f"{self.endpoint.rstrip('/')}/{path.lstrip('/')}" if path else self.endpoint
        body_template = (
            request_config.get("bodyTemplate")
            or request_config.get("messageTemplate")
            or '{"prompt":"{{ prompt }}"}'
        )
        body = body_template.replace("{{ prompt }}", prompt).replace("{{prompt}}", prompt).encode(
            "utf-8"
        )
        headers = {"content-type": "application/json", **(request_config.get("headers") or {})}
        auth = self.config.get("auth") or {}
        if auth.get("type") == "bearer" and self.token:
            headers[auth.get("headerName") or "authorization"] = f"Bearer {self.token}"
        if auth.get("type") == "api-key" and self.token:
            headers[auth.get("headerName") or "x-api-key"] = self.token
        if auth.get("type") == "cookie" and self.token:
            headers[auth.get("headerName") or "Cookie"] = self.token
        req = request.Request(
            url,
            data=body,
            headers=headers,
            method=request_config.get("method", "POST"),
        )
        with request.urlopen(req, timeout=self.timeout) as response:
            return response.read().decode("utf-8")

    def _extract_response(self, raw: str) -> str:
        response_config = self.config.get("response") or {}
        if response_config.get("type") == "text":
            return raw
        if response_config.get("type") == "event-data":
            for line in raw.splitlines():
                if line.startswith("data:"):
                    return line.replace("data:", "", 1).strip()
            return raw
        try:
            data = json.loads(raw)
        except Exception:
            return raw
        primary = self._read_json_path(data, response_config.get("path", "$.output"))
        if primary is not None:
            return str(primary)
        fallback_path = response_config.get("fallbackPath")
        if fallback_path:
            fallback = self._read_json_path(data, fallback_path)
            if fallback is not None:
                return str(fallback)
        return ""

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
