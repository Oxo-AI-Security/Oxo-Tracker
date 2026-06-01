from functools import lru_cache
from pathlib import Path
import shutil
from typing import Awaitable, Callable, Any

from moonshot.api import (
    api_create_runner,
    api_get_all_cookbook,
    api_get_all_endpoint,
    api_get_all_recipe,
    api_set_environment_variables,
)

from app.core.config import PROJECT_ROOT, get_moonshot_env


ASSET_DIR = Path(__file__).resolve().parent / "assets"
CONFIGURABLE_CONNECTOR_ASSET = ASSET_DIR / "configurable-app-connector.py"


def ensure_project_moonshot_assets() -> None:
    moonshot_env = get_moonshot_env()
    connector_dir = moonshot_env.get("CONNECTORS")
    if not connector_dir:
        return

    target_dir = Path(connector_dir)
    if not target_dir.is_absolute():
        target_dir = PROJECT_ROOT / target_dir

    if not target_dir.exists() or not CONFIGURABLE_CONNECTOR_ASSET.exists():
        return

    target = target_dir / CONFIGURABLE_CONNECTOR_ASSET.name
    asset_content = CONFIGURABLE_CONNECTOR_ASSET.read_text(encoding="utf-8")
    if not target.exists() or target.read_text(encoding="utf-8") != asset_content:
        shutil.copyfile(CONFIGURABLE_CONNECTOR_ASSET, target)


@lru_cache
def initialize_moonshot() -> bool:
    ensure_project_moonshot_assets()
    api_set_environment_variables(get_moonshot_env())
    return True


class MoonshotClient:
    def __init__(self) -> None:
        initialize_moonshot()

    def list_endpoints(self) -> list[dict]:
        return api_get_all_endpoint()

    def list_recipes(self) -> list[dict]:
        return api_get_all_recipe()

    def list_cookbooks(self) -> list[dict]:
        return api_get_all_cookbook()

    async def run_recipes(
        self,
        run_name: str,
        endpoints: list[str],
        recipes: list[str],
        description: str = "",
        prompt_selection_percentage: int = 100,
        random_seed: int = 0,
        system_prompt: str = "",
        on_runner_created: Callable[[Any], Awaitable[None]] | None = None,
    ) -> dict:
        runner = api_create_runner(
            name=run_name,
            endpoints=endpoints,
            description=description,
        )
        if on_runner_created:
            await on_runner_created(runner)
        await runner.run_recipes(
            recipes=recipes,
            prompt_selection_percentage=prompt_selection_percentage,
            random_seed=random_seed,
            system_prompt=system_prompt,
        )
        return {"runner_id": runner.id, "status": "completed"}

    async def run_cookbooks(
        self,
        run_name: str,
        endpoints: list[str],
        cookbooks: list[str],
        description: str = "",
        prompt_selection_percentage: int = 100,
        cookbook_prompt_selection_percentages: dict[str, int] | None = None,
        random_seed: int = 0,
        system_prompt: str = "",
        on_runner_created: Callable[[Any], Awaitable[None]] | None = None,
    ) -> dict:
        runner = api_create_runner(
            name=run_name,
            endpoints=endpoints,
            description=description,
        )
        if on_runner_created:
            await on_runner_created(runner)
        await runner.run_cookbooks(
            cookbooks=cookbooks,
            prompt_selection_percentage=prompt_selection_percentage,
            cookbook_prompt_selection_percentages=cookbook_prompt_selection_percentages or {},
            random_seed=random_seed,
            system_prompt=system_prompt,
        )
        return {"runner_id": runner.id, "status": "completed"}
