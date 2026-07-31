import pytest
from fastapi import HTTPException

from app.api.routes import benchmarks


def test_job_detail_returns_saved_summary_when_runner_artifact_is_missing(monkeypatch) -> None:
    job = {
        "id": "Oxo-AI-test-1",
        "runner_id": "Oxo-AI-test-1",
        "status": "running",
        "errors": [],
    }

    class FakeJobStore:
        def get(self, job_id: str) -> dict:
            assert job_id == job["id"]
            return job

        def enrich_job(self, saved_job: dict, **_: object) -> dict:
            assert saved_job is job
            raise FileNotFoundError("runner artifact is not ready")

        def compact_job(self, saved_job: dict) -> dict:
            return {**saved_job, "partial": True}

    monkeypatch.setattr(benchmarks, "JobStore", FakeJobStore)

    result = benchmarks.get_benchmark_job(job["id"])

    assert result["id"] == job["id"]
    assert result["status"] == "running"
    assert result["partial"] is True


def test_job_detail_returns_404_only_when_the_saved_job_is_missing(monkeypatch) -> None:
    class MissingJobStore:
        def get(self, job_id: str) -> dict:
            raise FileNotFoundError(job_id)

    monkeypatch.setattr(benchmarks, "JobStore", MissingJobStore)

    with pytest.raises(HTTPException) as caught:
        benchmarks.get_benchmark_job("missing-job")

    assert caught.value.status_code == 404
