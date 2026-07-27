from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    agent_security_review,
    benchmarks,
    health,
    moonshot_explicit,
    settings as settings_route,
    task_agents,
)
from app.core.config import get_settings
from app.integrations.moonshot.client import initialize_moonshot
from app.services.task_agent_runtime import get_task_agent_runtime, shutdown_task_agent_runtime


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    initialize_moonshot()
    runtime = get_task_agent_runtime()
    runtime.recover()
    try:
        yield
    finally:
        shutdown_task_agent_runtime()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(moonshot_explicit.router, prefix="/api/v1")
    app.include_router(benchmarks.router, prefix="/api/v1")
    app.include_router(settings_route.router, prefix="/api/v1")
    app.include_router(agent_security_review.router, prefix="/api/v1")
    app.include_router(task_agents.router, prefix="/api/v1")
    return app


app = create_app()
