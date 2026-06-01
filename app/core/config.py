from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


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
    return dict(dotenv_values(settings.moonshot_env_file))
