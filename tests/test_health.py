from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_explicit_moonshot_routes_are_registered() -> None:
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200

    paths = response.json()["paths"]
    assert "/api/v1/moonshot/endpoints" in paths
    assert "/api/v1/moonshot/recipes" in paths
    assert "/api/v1/moonshot/runners" in paths
    assert "/api/v1/moonshot/bookmarks" in paths
    assert not any(path.startswith("/api/v1/moonshot-api/") for path in paths)


def test_explicit_moonshot_route_can_call_service() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/moonshot/connectors/types")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
