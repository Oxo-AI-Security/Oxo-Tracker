from fastapi import APIRouter, BackgroundTasks, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from app.services.agent_security_review_store import MODEL_PROVIDERS, AgentSecurityReviewStore
from app.services.file_extraction import extract_text
from app.services.gemini_service import GeminiService

router = APIRouter(prefix="/agent-security-review", tags=["Agent Security Review"])


def store() -> AgentSecurityReviewStore:
    return AgentSecurityReviewStore()


def run_function_review_job(project_id: str, job_id: str) -> None:
    review_store = store()
    try:
        if review_store.is_review_cancelled(project_id, job_id):
            return
        project = review_store.get_project(project_id)
        review = GeminiService(review_store).run_material_question_review(project, review_store.project_dir(project_id), job_id=job_id)
        if review_store.is_review_cancelled(project_id, job_id):
            return
        review_store.save_function_review(project_id, review)
    except Exception as error:  # noqa: BLE001
        if review_store.is_review_cancelled(project_id, job_id):
            return
        review_store.update_project(project_id, {"status": "Error", "error": str(error)})


def run_risk_review_job(project_id: str, job_id: str) -> None:
    review_store = store()
    try:
        if review_store.is_review_cancelled(project_id, job_id):
            return
        project = review_store.get_project(project_id)
        review = GeminiService(review_store).run_risk_review(project, job_id=job_id)
        if review_store.is_review_cancelled(project_id, job_id):
            return
        review_store.save_risk_review(project_id, review)
    except Exception as error:  # noqa: BLE001
        if review_store.is_review_cancelled(project_id, job_id):
            return
        review_store.update_project(project_id, {"status": "Error", "error": str(error)})


def run_update_function_review_job(project_id: str, payload: dict, job_id: str) -> None:
    review_store = store()
    try:
        if review_store.is_review_cancelled(project_id, job_id):
            return
        project = review_store.get_project(project_id)
        review = GeminiService(review_store).update_function_map(project, review_store.project_dir(project_id), payload, job_id=job_id)
        if review_store.is_review_cancelled(project_id, job_id):
            return
        review_store.save_function_review(project_id, review)
    except Exception as error:  # noqa: BLE001
        if review_store.is_review_cancelled(project_id, job_id):
            return
        review_store.update_project(project_id, {"status": "Error", "error": str(error)})


@router.post("/projects")
def create_project(payload: dict = Body(...)) -> dict:
    project = store().create_project(payload)
    return {"projectId": project["projectId"]}


@router.get("/projects")
def list_projects() -> list[dict]:
    return store().list_projects()


@router.get("/projects/{project_id}")
def get_project(project_id: str) -> dict:
    try:
        return store().get_project(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.delete("/projects/{project_id}")
def delete_project(project_id: str) -> dict:
    try:
        return store().delete_project(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.patch("/projects/{project_id}")
def update_project(project_id: str, payload: dict = Body(...)) -> dict:
    try:
        review_store = store()
        if "provider" in payload or "modelName" in payload or "model" in payload or "temperature" in payload:
            review_store.save_model_settings(project_id, payload)
        current = review_store.save_manual_context(project_id, payload)
        return current
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.post("/projects/{project_id}/materials")
async def upload_materials(project_id: str, files: list[UploadFile] = File(...), tag: str = Form("Other")) -> dict:
    try:
        saved = []
        review_store = store()
        for upload in files:
            saved.append(await review_store.add_material(project_id, upload, tag))
        return {"materials": saved}
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.delete("/projects/{project_id}/materials/{file_id}")
def delete_material(project_id: str, file_id: str) -> dict:
    try:
        return store().delete_material(project_id, file_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Material not found") from error


@router.get("/projects/{project_id}/materials/{file_id}/file")
def get_material_file(project_id: str, file_id: str) -> FileResponse:
    try:
        review_store = store()
        project = review_store.get_project(project_id)
        material = next((item for item in project.get("materials", []) if item.get("fileId") == file_id), None)
        if not material:
            raise FileNotFoundError(file_id)
        file_path = review_store.project_dir(project_id) / "materials" / material["storedName"]
        if not file_path.is_file():
            raise FileNotFoundError(file_id)
        return FileResponse(
            file_path,
            media_type=material.get("contentType") or None,
            filename=material.get("fileName") or file_path.name,
            content_disposition_type="inline",
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Material not found") from error


@router.get("/projects/{project_id}/materials/{file_id}/preview", response_class=PlainTextResponse)
def preview_material_file(project_id: str, file_id: str) -> str:
    try:
        review_store = store()
        project = review_store.get_project(project_id)
        material = next((item for item in project.get("materials", []) if item.get("fileId") == file_id), None)
        if not material:
            raise FileNotFoundError(file_id)
        file_path = review_store.project_dir(project_id) / "materials" / material["storedName"]
        if not file_path.is_file():
            raise FileNotFoundError(file_id)
        text, supported, note = extract_text(file_path)
        if supported and text:
            return text
        return note or "Preview is not available for this file."
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Material not found") from error


@router.post("/settings/gemini")
def save_gemini_settings(payload: dict = Body(...)) -> dict:
    return store().save_gemini_api_key(str(payload.get("apiKey") or ""))


@router.post("/settings/gemini/test")
def test_gemini_settings() -> dict:
    try:
        return GeminiService(store()).test_connection()
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/settings/models")
def get_model_providers() -> dict:
    return {"providers": MODEL_PROVIDERS}


@router.post("/settings/api-key")
def save_provider_api_key(payload: dict = Body(...)) -> dict:
    provider = str(payload.get("provider") or "gemini")
    return store().save_provider_api_key(provider, str(payload.get("apiKey") or ""))


@router.post("/settings/test")
def test_provider_settings(payload: dict = Body(default={})) -> dict:
    try:
        return GeminiService(store()).test_connection(payload)
    except Exception as error:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/projects/{project_id}/function-review")
def function_review(background_tasks: BackgroundTasks, project_id: str, payload: dict = Body(default={})) -> dict:
    review_store = store()
    try:
        if payload:
            review_store.save_manual_context(project_id, payload)
        job_id = review_store.begin_review_job(project_id, "asset_review_running")
        background_tasks.add_task(run_function_review_job, project_id, job_id)
        return review_store.get_project(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001
        review_store.update_project(project_id, {"status": "Error", "error": str(error)})
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/projects/{project_id}/function-map")
def save_function_map(project_id: str, payload: dict = Body(...)) -> dict:
    try:
        return store().save_function_map(project_id, payload)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.post("/projects/{project_id}/function-map/update")
def update_function_map(background_tasks: BackgroundTasks, project_id: str, payload: dict = Body(...)) -> dict:
    review_store = store()
    try:
        review_store.save_manual_context(project_id, payload)
        mode = str(payload.get("mode") or "review_again")
        project = review_store.get_project(project_id)
        if mode == "direct" and review_store.has_unanswered_missing_questions(project.get("functionReview") or {}, project.get("missingAnswers") or {}):
            raise HTTPException(status_code=409, detail="Please answer all supplemental questions before generating the asset graph.")
        status = "asset_review_gap_check_running" if mode == "review_again" else "asset_review_assets_running"
        job_id = review_store.begin_review_job(project_id, status)
        background_tasks.add_task(run_update_function_review_job, project_id, payload, job_id)
        return review_store.get_project(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error
    except Exception as error:  # noqa: BLE001
        review_store.update_project(project_id, {"status": "Error", "error": str(error)})
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/projects/{project_id}/risk-review")
def risk_review(background_tasks: BackgroundTasks, project_id: str, payload: dict = Body(default={})) -> dict:
    review_store = store()
    try:
        if payload:
            review_store.save_manual_context(project_id, payload)
        project = review_store.get_project(project_id)
        if not project.get("functionReview"):
            raise HTTPException(status_code=409, detail="Asset Review must be completed first")
        if review_store.has_blocking_missing_questions(project.get("functionReview") or {}, project.get("missingAnswers") or {}):
            raise HTTPException(status_code=409, detail="Risk Map is not ready. Please answer critical missing information first.")
        function_review = project.get("functionReview") or {}
        if not function_review.get("features"):
            raise HTTPException(status_code=409, detail="Risk Map is not ready. At least one capability is required.")
        if not (
            function_review.get("asset_graph_nodes")
            or function_review.get("relationships")
            or (function_review.get("vueFlow") or {}).get("nodes")
            or (project.get("functionMap") or {}).get("nodes")
        ):
            raise HTTPException(status_code=409, detail="Risk Map is not ready. Asset graph nodes or relationships are required.")
        job_id = review_store.begin_review_job(project_id, "risk_reviewing")
        background_tasks.add_task(run_risk_review_job, project_id, job_id)
        return review_store.get_project(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error
    except HTTPException:
        raise
    except Exception as error:  # noqa: BLE001
        review_store.update_project(project_id, {"status": "Error", "error": str(error)})
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/projects/{project_id}/review/cancel")
def cancel_review(project_id: str) -> dict:
    try:
        return store().cancel_review_job(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.get("/projects/{project_id}/report", response_class=PlainTextResponse)
def get_report(project_id: str) -> str:
    try:
        return store().get_project(project_id).get("reportMarkdown", "")
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error
