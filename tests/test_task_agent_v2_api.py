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
