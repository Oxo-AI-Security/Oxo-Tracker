from app.integrations.moonshot import client


def test_project_moonshot_assets_include_privacy_evaluator(tmp_path, monkeypatch) -> None:
    connector_dir = tmp_path / "connectors"
    metric_dir = tmp_path / "metrics"
    connector_dir.mkdir()
    metric_dir.mkdir()
    monkeypatch.setattr(
        client,
        "get_moonshot_env",
        lambda: {
            "CONNECTORS": str(connector_dir),
            "METRICS": str(metric_dir),
        },
    )

    client.ensure_project_moonshot_assets()

    assert (
        connector_dir / client.CONFIGURABLE_CONNECTOR_ASSET.name
    ).read_text(encoding="utf-8") == client.CONFIGURABLE_CONNECTOR_ASSET.read_text(
        encoding="utf-8"
    )
    assert (
        metric_dir / client.PRIVACY_EVALUATOR_ASSET.name
    ).read_text(encoding="utf-8") == client.PRIVACY_EVALUATOR_ASSET.read_text(
        encoding="utf-8"
    )
