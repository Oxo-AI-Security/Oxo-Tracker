from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.paths import APP_PATHS, MOONSHOT_DATA_ROOT, PROJECT_ROOT


MOONSHOT_PATHS = {
    "ATTACK_MODULES": "attack-modules",
    "BOOKMARKS": "generated-outputs/bookmarks",
    "CONNECTORS": "connectors",
    "CONNECTORS_ENDPOINTS": "connectors-endpoints",
    "CONTEXT_STRATEGY": "context-strategy",
    "COOKBOOKS": "cookbooks",
    "DATABASES": "generated-outputs/databases",
    "DATABASES_MODULES": "databases-modules",
    "DATASETS": "datasets",
    "IO_MODULES": "io-modules",
    "METRICS": "metrics",
    "PROMPT_TEMPLATES": "prompt-templates",
    "RECIPES": "recipes",
    "RESULTS": "generated-outputs/results",
    "RESULTS_MODULES": "results-modules",
    "RUNNERS": "generated-outputs/runners",
    "RUNNERS_MODULES": "runners-modules",
}


class Settings(BaseSettings):
    app_name: str = Field(default="Oxo Tracker", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    moonshot_env_file: Path = PROJECT_ROOT / ".env"

    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_moonshot_env() -> dict:
    settings = get_settings()
    configured = {
        key: value
        for key, value in dotenv_values(settings.moonshot_env_file).items()
        if value is not None
    }
    if APP_PATHS.desktop_mode:
        configured.update(
            {
                key: str((MOONSHOT_DATA_ROOT / relative).resolve())
                for key, relative in MOONSHOT_PATHS.items()
            }
        )
    return configured
