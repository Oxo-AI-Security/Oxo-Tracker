from fastapi import APIRouter, BackgroundTasks, HTTPException, Response

from app.schemas.benchmark import BenchmarkRecipeRequest, BenchmarkRunResponse
from app.services.benchmark_service import BenchmarkService
from app.services.job_runtime import job_runtime
from app.services.job_store import JobStore

router = APIRouter(prefix="/benchmarks", tags=["Benchmarks"])


@router.post("/recipes", response_model=BenchmarkRunResponse)
async def run_recipe_benchmark(request: BenchmarkRecipeRequest, background_tasks: BackgroundTasks) -> dict:
    service = BenchmarkService()
    job = service.create_recipe_job(request)
    background_tasks.add_task(service.execute_recipe_job, job["id"])
    return {"runner_id": job["id"], "status": job["status"]}


@router.get("/jobs")
def list_benchmark_jobs() -> list[dict]:
    return JobStore().list_jobs()


@router.get("/jobs/{job_id}")
def get_benchmark_job(
    job_id: str,
    interactions_page: int = 1,
    interactions_page_size: int = 100,
    interaction_filter: str = "all",
    cookbook_filter: str = "all",
) -> dict:
    store = JobStore()
    try:
        return store.enrich_job(
            store.get(job_id),
            interactions_page=interactions_page,
            interactions_page_size=interactions_page_size,
            interaction_filter=interaction_filter,
            cookbook_filter=cookbook_filter,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found") from error


@router.post("/jobs/{job_id}/pause")
async def pause_benchmark_job(job_id: str) -> dict:
    store = JobStore()
    try:
        job = store.get(job_id)
        if job.get("status") not in {"queued", "running", "running_with_errors"}:
            return store.enrich_job(job)
        cancelled = await job_runtime.cancel(job_id)
        paused = store.mark_paused(job_id, "Paused by user")
        paused["runtime_cancelled"] = cancelled
        return store.enrich_job(paused)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found") from error


@router.post("/jobs/{job_id}/resume")
async def resume_benchmark_job(job_id: str, background_tasks: BackgroundTasks) -> dict:
    store = JobStore()
    try:
        job = store.get(job_id)
        if job.get("status") != "paused":
            return store.enrich_job(job)
        resumed = store.mark_resumed(job_id)
        background_tasks.add_task(BenchmarkService().execute_recipe_job, job_id)
        return store.enrich_job(resumed)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found") from error


@router.patch("/jobs/{job_id}/thread-count")
def update_benchmark_job_thread_count(job_id: str, payload: dict) -> dict:
    store = JobStore()
    try:
        job = store.get(job_id)
        if job.get("status") != "paused":
            raise HTTPException(status_code=409, detail="Thread count can only be changed while the job is paused")
        thread_count = int(payload.get("thread_count") or 1)
        return store.enrich_job(store.update_thread_count(job_id, thread_count))
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found") from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid thread count") from error


@router.get("/jobs/{job_id}/report/download")
def download_benchmark_job_report(job_id: str) -> Response:
    store = JobStore()
    try:
        report_html = store.render_report_html(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Report not found") from error
    filename = f"benchmark-report-{job_id}.html"
    return Response(
        content=report_html,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/jobs/{job_id}")
def delete_benchmark_job(job_id: str) -> dict:
    store = JobStore()
    try:
        return store.delete_job(job_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Job not found") from error
