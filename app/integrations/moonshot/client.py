from functools import lru_cache
from inspect import signature
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
from moonshot.src.configs.env_variables import EnvVariables
from moonshot.src.runners.runner_type import RunnerType
from moonshot.src.runs.run import Run
from moonshot.src.storage.storage import Storage

from app.core.config import get_moonshot_env
from app.core.paths import APP_HOME


ASSET_DIR = Path(__file__).resolve().parent / "assets"
CONFIGURABLE_CONNECTOR_ASSET = ASSET_DIR / "configurable-app-connector.py"
PRIVACY_EVALUATOR_ASSET = ASSET_DIR / "mlcprv-annotator.py"


def ensure_project_moonshot_assets() -> None:
    moonshot_env = get_moonshot_env()
    managed_assets = (
        ("CONNECTORS", CONFIGURABLE_CONNECTOR_ASSET),
        ("METRICS", PRIVACY_EVALUATOR_ASSET),
    )
    for environment_key, asset in managed_assets:
        configured_dir = moonshot_env.get(environment_key)
        if not configured_dir or not asset.exists():
            continue

        target_dir = Path(configured_dir)
        if not target_dir.is_absolute():
            target_dir = APP_HOME / target_dir
        if not target_dir.exists():
            continue

        target = target_dir / asset.name
        asset_content = asset.read_text(encoding="utf-8")
        if not target.exists() or target.read_text(encoding="utf-8") != asset_content:
            shutil.copyfile(asset, target)


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
        percentages = cookbook_prompt_selection_percentages or {}
        run_cookbooks_parameters = signature(runner.run_cookbooks).parameters
        if "cookbook_prompt_selection_percentages" in run_cookbooks_parameters:
            await runner.run_cookbooks(
                cookbooks=cookbooks,
                prompt_selection_percentage=prompt_selection_percentage,
                cookbook_prompt_selection_percentages=percentages,
                random_seed=random_seed,
                system_prompt=system_prompt,
            )
        elif percentages:
            await _run_cookbooks_with_per_cookbook_percentages(
                runner,
                cookbooks=cookbooks,
                prompt_selection_percentage=prompt_selection_percentage,
                cookbook_prompt_selection_percentages=percentages,
                random_seed=random_seed,
                system_prompt=system_prompt,
            )
        else:
            await runner.run_cookbooks(
                cookbooks=cookbooks,
                prompt_selection_percentage=prompt_selection_percentage,
                random_seed=random_seed,
                system_prompt=system_prompt,
            )
        return {"runner_id": runner.id, "status": "completed"}


async def _run_cookbooks_with_per_cookbook_percentages(
    runner: Any,
    *,
    cookbooks: list[str],
    prompt_selection_percentage: int,
    cookbook_prompt_selection_percentages: dict[str, int],
    random_seed: int,
    system_prompt: str,
) -> None:
    """Run extended cookbook arguments without patching the bundled Moonshot package."""
    async with runner.current_operation_lock:
        operation = Run(
            runner.id,
            RunnerType.BENCHMARK,
            {
                "cookbooks": cookbooks,
                "prompt_selection_percentage": prompt_selection_percentage,
                "cookbook_prompt_selection_percentages": cookbook_prompt_selection_percentages,
                "random_seed": random_seed,
                "system_prompt": system_prompt,
                "runner_processing_module": "benchmarking",
                "result_processing_module": "benchmarking-result",
            },
            runner.database_instance,
            runner.endpoints,
            Storage.get_filepath(EnvVariables.RESULTS.name, runner.id, "json", True),
            runner.progress_callback_func,
        )
        runner.current_operation = operation

    try:
        await operation.run()
    finally:
        async with runner.current_operation_lock:
            if runner.current_operation is operation:
                runner.current_operation = None
