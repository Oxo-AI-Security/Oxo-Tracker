from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.schemas.task_agent_v2 import (
    ExecutorSkillDuplicateRequest,
    ExecutorSkillWriteRequest,
    TaskControlRequest,
    TaskCreateRequest,
    TaskSteerRequest,
)
from app.services.executor_skill_service import ExecutorSkillService, SkillStoreError
from app.services.prompt_registry import PromptRegistry
from app.services.task_agent_graph import workflow_definition
from app.services.task_agent_runtime import get_task_agent_runtime
from app.services.task_agent_store import ActiveTaskExistsError


router = APIRouter(prefix="/task-agents", tags=["Task Agents V2"])


@router.post("/tasks", status_code=status.HTTP_202_ACCEPTED)
def create_task(request: TaskCreateRequest):
    try:
        return get_task_agent_runtime().create(request)
    except ActiveTaskExistsError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": str(error), "activeTaskId": error.task_id},
        ) from error


@router.get("/tasks")
def list_tasks(
    session_id: str | None = None,
    chat_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    return get_task_agent_runtime().list(
        session_id=session_id,
        chat_id=chat_id,
        limit=limit,
    )


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    try:
        return get_task_agent_runtime().get(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error


@router.post("/tasks/{task_id}/pause", status_code=status.HTTP_202_ACCEPTED)
def pause_task(task_id: str):
    try:
        return get_task_agent_runtime().pause(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error


@router.post("/tasks/{task_id}/resume", status_code=status.HTTP_202_ACCEPTED)
def resume_task(task_id: str):
    try:
        return get_task_agent_runtime().resume(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/tasks/{task_id}/stop", status_code=status.HTTP_202_ACCEPTED)
def stop_task(task_id: str, request: TaskControlRequest | None = None):
    try:
        return get_task_agent_runtime().stop(
            task_id,
            request.reason if request else None,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error


@router.post("/tasks/{task_id}/steer", status_code=status.HTTP_202_ACCEPTED)
def steer_task(task_id: str, request: TaskSteerRequest):
    try:
        return get_task_agent_runtime().steer(task_id, request.instruction)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/tasks/{parent_task_id}/adopt-success/{child_task_id}",
    status_code=status.HTTP_200_OK,
)
def adopt_branch_success(parent_task_id: str, child_task_id: str):
    try:
        return get_task_agent_runtime().adopt_branch_success(
            parent_task_id,
            child_task_id,
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post(
    "/tasks/{task_id}/reconcile-evidence",
    status_code=status.HTTP_200_OK,
)
def reconcile_task_evidence(task_id: str):
    try:
        return get_task_agent_runtime().reconcile_existing_evidence(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.get("/tasks/{task_id}/traces")
def list_task_traces(
    task_id: str,
    limit: int = Query(default=1_000, ge=1, le=10_000),
):
    runtime = get_task_agent_runtime()
    try:
        runtime.store.get_snapshot(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    return runtime.store.list_traces(task_id, limit=limit)


@router.get("/tasks/{task_id}/events")
def list_task_events(
    task_id: str,
    after_id: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=5_000),
):
    runtime = get_task_agent_runtime()
    try:
        runtime.store.get_snapshot(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    return runtime.store.list_events(
        task_id,
        after_id=after_id,
        limit=limit,
    )


@router.get("/tasks/{task_id}/branch-reports")
def list_task_branch_reports(task_id: str):
    runtime = get_task_agent_runtime()
    try:
        runtime.store.get_snapshot(task_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="Task not found") from error
    return runtime.store.list_branch_reports(task_id)


@router.get("/workflow")
def get_workflow():
    return workflow_definition()


@router.get("/prompts")
def get_prompt_versions():
    return PromptRegistry().versions()


@router.get("/success-memories")
def list_success_memories(
    target_key: str = Query(min_length=1, max_length=2_000),
    runner_id: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
):
    return get_task_agent_runtime().store.list_success_memories(
        target_key=target_key,
        runner_id=runner_id,
        limit=limit,
    )


@router.delete("/success-memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_success_memory(memory_id: str):
    try:
        get_task_agent_runtime().store.delete_success_memory(memory_id)
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Success memory not found",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/success-memories/{memory_id}/status")
def update_success_memory_status(
    memory_id: str,
    status_value: str = Query(alias="status", pattern="^(suspect|verified|revoked)$"),
    reason: str = Query(default="", max_length=4_000),
):
    try:
        return get_task_agent_runtime().store.set_success_memory_status(
            memory_id,
            status_value,
            reason=reason,
        )
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail="Success memory not found",
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/stats")
def get_stats():
    runtime = get_task_agent_runtime()
    return {
        **runtime.store.stats(),
        "skillCount": len(ExecutorSkillService().list_catalog()),
    }


@router.get("/skills")
def list_skills():
    return ExecutorSkillService().list_catalog()


@router.post("/skills", status_code=status.HTTP_201_CREATED)
def create_skill(request: ExecutorSkillWriteRequest):
    try:
        return ExecutorSkillService().create(request.skill)
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail="Skill already exists") from error
    except SkillStoreError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/skills/validate")
def validate_skill(request: ExecutorSkillWriteRequest):
    return ExecutorSkillService().validate_skill(request.skill)


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str):
    try:
        return ExecutorSkillService().get(skill_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Skill not found") from error
    except SkillStoreError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/skills/{skill_id}")
def update_skill(skill_id: str, request: ExecutorSkillWriteRequest):
    try:
        return ExecutorSkillService().update(skill_id, request.skill)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Skill not found") from error
    except SkillStoreError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/skills/{skill_id}/duplicate", status_code=status.HTTP_201_CREATED)
def duplicate_skill(skill_id: str, request: ExecutorSkillDuplicateRequest):
    try:
        return ExecutorSkillService().duplicate(skill_id, request)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Skill not found") from error
    except FileExistsError as error:
        raise HTTPException(status_code=409, detail="Duplicate target already exists") from error
    except SkillStoreError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(skill_id: str):
    try:
        ExecutorSkillService().delete(skill_id)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="Skill not found") from error
    except SkillStoreError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
