from __future__ import annotations

import os
import secrets
from collections.abc import Iterable

from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


DEFAULT_DESKTOP_ORIGINS = {
    "http://tauri.localhost",
    "https://tauri.localhost",
    "tauri://localhost",
    "http://127.0.0.1:5173",
    "http://localhost:5173",
}


def desktop_origins(extra: Iterable[str] = ()) -> set[str]:
    configured = {
        item.strip().rstrip("/")
        for item in os.getenv("OXO_DESKTOP_ORIGINS", "").split(",")
        if item.strip()
    }
    return DEFAULT_DESKTOP_ORIGINS | configured | set(extra)


class DesktopSecurityMiddleware:
    """Protect the desktop loopback API from unrelated local processes."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        token = os.getenv("OXO_DESKTOP_TOKEN", "")
        if scope["type"] != "http" or not token:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        host = headers.get("host", "").split(":", 1)[0].lower()
        if host not in {"127.0.0.1", "localhost"}:
            await self._reject(scope, receive, send, "Invalid desktop API host")
            return

        origin = headers.get("origin", "").rstrip("/")
        if origin and origin not in desktop_origins():
            await self._reject(scope, receive, send, "Invalid desktop API origin")
            return

        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        supplied = headers.get("x-oxo-desktop-token", "")
        if not supplied or not secrets.compare_digest(supplied, token):
            await self._reject(scope, receive, send, "Desktop API authentication failed")
            return

        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(
        scope: Scope,
        receive: Receive,
        send: Send,
        detail: str,
    ) -> None:
        response = JSONResponse({"detail": detail}, status_code=403)
        await response(scope, receive, send)
