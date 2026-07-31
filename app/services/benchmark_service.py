import asyncio

from app.integrations.moonshot.client import MoonshotClient
from app.schemas.benchmark import BenchmarkRecipeRequest
from app.services.endpoint_tuning import apply_endpoint_thread_count
from app.services.job_runtime import job_runtime
from app.services.job_store import JobStore
from app.services.moonshot_api_service import MoonshotApiService
from app.services.settings_store import SettingsStore


class BenchmarkService:
    def __init__(
        self,
        moonshot_client: MoonshotClient | None = None,
        job_store: JobStore | None = None,
        settings_store: SettingsStore | None = None,
        moonshot_api_service: MoonshotApiService | None = None,
    ) -> None:
        self.moonshot_client = moonshot_client or MoonshotClient()
        self.job_store = job_store or JobStore()
        self.settings_store = settings_store or SettingsStore()
        self._moonshot_api_service = moonshot_api_service

    def create_recipe_job(self, request: BenchmarkRecipeRequest) -> dict:
        self._resolve_evaluator_settings(request)
        return self.job_store.create_job(request)

    async def execute_recipe_job(self, job_id: str) -> None:
        job = self.job_store.get(job_id)
        if job.get("status") == "paused":
            return
        request = BenchmarkRecipeRequest(**job["request"])
        runner_id = job["runner_id"]
        try:
            self._configure_evaluator_endpoints(request)
            apply_endpoint_thread_count(request.endpoints, request.thread_count)
            self.job_store.mark_started(job_id, runner_id)
            if request.cookbooks:
                await self.moonshot_client.run_cookbooks(
                    run_name=runner_id,
                    endpoints=request.endpoints,
                    cookbooks=request.cookbooks,
                    description=request.description,
                    prompt_selection_percentage=request.prompt_selection_percentage,
                    cookbook_prompt_selection_percentages=request.cookbook_prompt_selection_percentages,
                    random_seed=request.random_seed,
                    system_prompt=request.system_prompt,
                    on_runner_created=lambda runner: job_runtime.register(job_id, runner),
                )
            else:
                await self.moonshot_client.run_recipes(
                    run_name=runner_id,
                    endpoints=request.endpoints,
                    recipes=request.recipes,
                    description=request.description,
                    prompt_selection_percentage=request.prompt_selection_percentage,
                    random_seed=request.random_seed,
                    system_prompt=request.system_prompt,
                    on_runner_created=lambda runner: job_runtime.register(job_id, runner),
                )
            if self.job_store.get(job_id).get("status") == "paused":
                return
            enriched = self.job_store.enrich_job(self.job_store.get(job_id), include_interactions=False)
            final_status = "completed"
            if enriched.get("errors"):
                final_status = "completed_with_errors"
            self.job_store.mark_completed(job_id, runner_id, final_status)
        except Exception as error:
            self.job_store.mark_failed(job_id, error)
        finally:
            await job_runtime.unregister(job_id)

    async def execute_recipe_job_background(self, job_id: str) -> None:
        """Run Moonshot in a worker thread so API polling remains responsive."""
        await asyncio.to_thread(self._execute_recipe_job_in_worker, job_id)

    def _execute_recipe_job_in_worker(self, job_id: str) -> None:
        asyncio.run(self.execute_recipe_job(job_id))

    async def run_recipe_benchmark(self, request: BenchmarkRecipeRequest) -> dict:
        job = self.create_recipe_job(request)
        await self.execute_recipe_job_background(job["id"])
        return {"runner_id": job["id"], "status": self.job_store.get(job["id"])["status"]}

    async def run_recipe_benchmark_sync(self, request: BenchmarkRecipeRequest) -> dict:
        return await self.moonshot_client.run_recipes(
            run_name=request.run_name,
            endpoints=request.endpoints,
            recipes=request.recipes,
            description=request.description,
            prompt_selection_percentage=request.prompt_selection_percentage,
            random_seed=request.random_seed,
            system_prompt=request.system_prompt,
        )

    def _resolve_evaluator_settings(
        self,
        request: BenchmarkRecipeRequest,
    ) -> dict[str, str] | None:
        endpoint_ids = _unique_non_empty(request.evaluator_endpoints)
        if not endpoint_ids:
            return None
        provider = str(request.evaluator_provider or "").strip()
        model = str(request.evaluator_model or "").strip()
        if not provider or not model:
            raise ValueError(
                "Evaluator provider and model are required for the selected cookbook."
            )
        return self.settings_store.get_ai_settings(provider, model=model)

    def _configure_evaluator_endpoints(
        self,
        request: BenchmarkRecipeRequest,
    ) -> None:
        endpoint_ids = _unique_non_empty(request.evaluator_endpoints)
        if not endpoint_ids:
            return

        settings = self._resolve_evaluator_settings(request)
        if settings is None:
            return
        service = self._moonshot_api_service or MoonshotApiService()
        current_endpoints = service.get_all_endpoint()

        for required_id in endpoint_ids:
            endpoint = next(
                (
                    item
                    for item in current_endpoints
                    if _endpoint_matches(item, required_id)
                ),
                None,
            )
            payload = {
                "name": str((endpoint or {}).get("name") or required_id),
                "connector_type": "openai-connector",
                "uri": settings["base_url"],
                "token": settings["api_key"],
                "max_calls_per_second": int(
                    (endpoint or {}).get("max_calls_per_second") or 10
                ),
                "max_concurrency": int(
                    (endpoint or {}).get("max_concurrency") or 1
                ),
                "model": settings["model"],
                "params": dict(
                    (endpoint or {}).get("params")
                    or {
                        "timeout": 300,
                        "max_attempts": 3,
                        "temperature": 0.5,
                    }
                ),
            }
            if endpoint:
                service.update_endpoint(_endpoint_id(endpoint), payload)
            else:
                service.create_endpoint(payload)


def _unique_non_empty(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _endpoint_id(endpoint: dict) -> str:
    return str(endpoint.get("id") or endpoint.get("name") or "").strip()


def _endpoint_matches(endpoint: dict, required_id: str) -> bool:
    return required_id in {
        str(endpoint.get("id") or "").strip(),
        str(endpoint.get("name") or "").strip(),
    }
