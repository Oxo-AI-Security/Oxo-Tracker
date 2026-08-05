from fastapi import APIRouter, Body, HTTPException

from app.services.agent_security_review_store import MODEL_PROVIDERS, AgentSecurityReviewStore

router = APIRouter(prefix="/agent-security-review", tags=["Agent Security Review"])


def store() -> AgentSecurityReviewStore:
    return AgentSecurityReviewStore()


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


@router.get("/projects/{project_id}/canvas")
def get_canvas(project_id: str) -> dict:
    try:
        return store().get_canvas(project_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Project not found") from error


@router.put("/projects/{project_id}/canvas")
def save_canvas(project_id: str, payload: dict = Body(...)) -> dict:
    try:
        return store().save_canvas(project_id, payload)
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


@router.get("/settings/models")
def get_model_providers() -> dict:
    return {"providers": MODEL_PROVIDERS}
