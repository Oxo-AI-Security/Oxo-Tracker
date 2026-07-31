from fastapi.testclient import TestClient

from app.main import create_app


def test_workflow_and_skill_catalog_api():
    with TestClient(create_app()) as client:
        workflow = client.get("/api/v1/task-agents/workflow")
        skills = client.get("/api/v1/task-agents/skills")

    assert workflow.status_code == 200
    node_ids = {node["id"] for node in workflow.json()["nodes"]}
    assert {
        "planner",
        "skill_loader",
        "skill_composer",
        "executor",
        "target",
        "router",
    } <= node_ids
    assert skills.status_code == 200
    assert len(skills.json()) >= 8
    assert "system-prompt-disclosure-assessment" in {
        item["name"] for item in skills.json()
    }
    assert all("body" not in item for item in skills.json())
    assert all(item["metadata"]["techniques"] for item in skills.json())


def test_p1_run_asset_routes_are_exposed():
    with TestClient(create_app()) as client:
        document = client.get("/openapi.json").json()

    paths = set(document["paths"])
    assert {
        "/api/v1/task-agents/tasks/{task_id}/manifest",
        "/api/v1/task-agents/tasks/{task_id}/replay",
        "/api/v1/task-agents/tasks/{task_id}/regrade",
        "/api/v1/task-agents/tasks/{task_id}/fork",
        "/api/v1/task-agents/tasks/{task_id}/scorer-review",
        "/api/v1/task-agents/tasks/{task_id}/findings",
        "/api/v1/task-agents/campaigns",
        "/api/v1/task-agents/findings",
        "/api/v1/task-agents/findings/{finding_id}/regression-cases",
        "/api/v1/task-agents/regression-cases",
    } <= paths
