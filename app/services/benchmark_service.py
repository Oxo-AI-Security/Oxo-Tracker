from app.integrations.moonshot.client import MoonshotClient
from app.schemas.benchmark import BenchmarkRecipeRequest
from app.services.endpoint_tuning import apply_endpoint_thread_count
from app.services.job_runtime import job_runtime
from app.services.job_store import JobStore


class BenchmarkService:
    def __init__(
        self,
        moonshot_client: MoonshotClient | None = None,
        job_store: JobStore | None = None,
    ) -> None:
        self.moonshot_client = moonshot_client or MoonshotClient()
        self.job_store = job_store or JobStore()

    def create_recipe_job(self, request: BenchmarkRecipeRequest) -> dict:
        return self.job_store.create_job(request)

    async def execute_recipe_job(self, job_id: str) -> None:
        job = self.job_store.get(job_id)
        if job.get("status") == "paused":
            return
        request = BenchmarkRecipeRequest(**job["request"])
        runner_id = job["runner_id"]
        try:
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

    async def run_recipe_benchmark(self, request: BenchmarkRecipeRequest) -> dict:
        job = self.create_recipe_job(request)
        await self.execute_recipe_job(job["id"])
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
