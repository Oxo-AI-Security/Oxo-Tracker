from __future__ import annotations

import json
from time import perf_counter
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app.services.settings_store import PROVIDER_CATALOG


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


def _models_url(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Base URL must be a valid HTTP or HTTPS URL")
    return f"{cleaned}/models"


def _result_message(status_code: int) -> str:
    if status_code in {401, 403}:
        return "Authentication failed. Check the API key and endpoint."
    if status_code == 404:
        return "The models endpoint was not found. Check the Base URL."
    if status_code == 429:
        return "The provider rate limit was reached. Try again shortly."
    return f"Provider returned HTTP {status_code}."


def probe_ai_connection(
    provider_id: str,
    model: str,
    base_url: str,
    api_key: str,
    *,
    request_open: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if provider_id not in PROVIDER_CATALOG:
        raise ValueError("Unsupported AI provider")
    if not model.strip():
        raise ValueError("Model is required")
    if not api_key.strip():
        raise ValueError("API key is required")

    headers = {"Accept": "application/json", "User-Agent": "Oxo-Tracker/AI-Settings"}
    if provider_id == "azure_openai":
        headers["api-key"] = api_key.strip()
    else:
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    request = Request(_models_url(base_url), headers=headers, method="GET")
    opener = request_open or build_opener(_NoRedirectHandler()).open
    started = perf_counter()
    try:
        with opener(request, timeout=15) as response:
            status_code = int(response.status)
            payload = json.loads(response.read(1_000_001).decode("utf-8"))
    except HTTPError as error:
        latency_ms = round((perf_counter() - started) * 1000)
        return {
            "ok": False,
            "provider": provider_id,
            "model": model.strip(),
            "statusCode": int(error.code),
            "latencyMs": latency_ms,
            "modelAvailable": False,
            "message": _result_message(int(error.code)),
        }
    except (URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", None)
        detail = str(reason or error)
        raise ValueError(f"Unable to reach provider: {detail}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Provider returned an invalid models response") from error

    latency_ms = round((perf_counter() - started) * 1000)
    data = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids = {
        str(item.get("id"))
        for item in data
        if isinstance(item, dict) and item.get("id") is not None
    }
    model_available = model.strip() in model_ids
    return {
        "ok": 200 <= status_code < 300,
        "provider": provider_id,
        "model": model.strip(),
        "statusCode": status_code,
        "latencyMs": latency_ms,
        "modelAvailable": model_available,
        "message": (
            "Connection successful."
            if model_available
            else "Endpoint connected, but the selected model was not listed."
        ),
    }
