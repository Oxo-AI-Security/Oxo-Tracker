from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.routes import (
    agent_security_review,
    benchmarks,
    health,
    moonshot_explicit,
    settings as settings_route,
    task_agents,
)
from app.core.config import get_settings
from app.core.desktop_security import DesktopSecurityMiddleware, desktop_origins
from app.core.paths import APP_PATHS
from app.integrations.moonshot.client import initialize_moonshot
from app.services.task_agent_runtime import get_task_agent_runtime, shutdown_task_agent_runtime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    APP_PATHS.prepare_desktop_assets(os.getenv("OXO_ASSET_VERSION", "unversioned"))
    initialize_moonshot()
    runtime = None
    try:
        runtime = get_task_agent_runtime()
        runtime.recover()
    except ValueError as error:
        # A fresh desktop install intentionally ships without API credentials.
        # Let the settings UI open; the runtime will initialize lazily after the
        # user configures an online provider. Web/development behavior is kept.
        if not APP_PATHS.desktop_mode or not str(error).startswith(
            "No API key is configured for provider "
        ):
            raise
    try:
        yield
    finally:
        if runtime is not None:
            shutdown_task_agent_runtime()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(desktop_origins()),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )
    app.add_middleware(DesktopSecurityMiddleware)

    app.include_router(health.router)
    app.include_router(moonshot_explicit.router, prefix="/api/v1")
    app.include_router(benchmarks.router, prefix="/api/v1")
    app.include_router(settings_route.router, prefix="/api/v1")
    app.include_router(agent_security_review.router, prefix="/api/v1")
    app.include_router(task_agents.router, prefix="/api/v1")
    return app


app = create_app()
