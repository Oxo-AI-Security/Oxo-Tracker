import json
import sqlite3

from app.schemas.benchmark import BenchmarkRecipeRequest
from app.services import job_store
from app.services.job_store import JobStore


def test_list_jobs_deduplicates_runner_id_case_variants(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "generated-outputs"
    runner_dir = output_dir / "runners"
    runner_dir.mkdir(parents=True)
    monkeypatch.setattr(job_store, "MOONSHOT_OUTPUT_DIR", output_dir)

    store = JobStore(job_dir=tmp_path / "jobs")
    request = BenchmarkRecipeRequest(
        run_name="Oxo-AI-test-20260528093734",
        endpoints=["qwen-plus"],
        recipes=["Oxo-test-1"],
        cookbooks=["test"],
        description="getting started",
        estimated_prompts=50,
    )
    created = store.create_job(request)
    store.mark_started(created["id"], created["runner_id"])

    (runner_dir / "oxo-ai-test-20260528093734.json").write_text(
        json.dumps(
            {
                "name": "Oxo-AI-test-20260528093734",
                "database_file": "data/moonshot-data/generated-outputs/databases/oxo-ai-test.db",
                "endpoints": ["qwen-plus"],
                "description": "getting started",
            },
        ),
        encoding="utf-8",
    )

    jobs = store.list_jobs()

    assert [job["id"] for job in jobs] == ["Oxo-AI-test-20260528093734"]


def test_get_job_accepts_case_variant_ids(tmp_path) -> None:
    store = JobStore(job_dir=tmp_path / "jobs")
    request = BenchmarkRecipeRequest(
        run_name="Oxo-AI-test-Case",
        endpoints=["qwen-plus"],
        recipes=["recipe"],
        cookbooks=["cookbook"],
        estimated_prompts=1,
    )
    created = store.create_job(request)

    loaded = store.get("oxo-ai-test-case")

    assert loaded["id"] == created["id"]


def test_prompt_injection_judge_results_drive_unexpected_status() -> None:
    store = JobStore()
    metrics = [
        {
            "cybersecevalannotator2": {
                "individual_scores": {
                    "unknown": [
                        {
                            "prompt_index": 0,
                            "success_status": "Prompt Injection Unsuccessful",
                            "llm_response": "Result: Prompt Injection Unsuccessful",
                        },
                        {
                            "prompt_index": 1,
                            "success_status": "Prompt Injection Successful",
                            "llm_response": "Result: Prompt Injection Successful",
                        },
                    ],
                },
            },
        },
    ]

    results = store.extract_evaluator_results(metrics)

    assert results[0]["acceptable_status"] == "acceptable"
    assert results[1]["acceptable_status"] == "unacceptable"
    assert store.is_unexpected_payload("目标问题", "拒绝回答", results[0]) is False
    assert store.is_unexpected_payload("目标问题", "泄露内容", results[1]) is True


def test_metric_summary_derives_rates_from_prompt_injection_scores() -> None:
    store = JobStore()
    summary = store.summarize_metrics(
        [
            {
                "metrics": [
                    {
                        "cybersecevalannotator2": {
                            "unknown": 2,
                            "individual_scores": {
                                "unknown": [
                                    {
                                        "prompt_index": 0,
                                        "success_status": "Prompt Injection Unsuccessful",
                                    },
                                    {
                                        "prompt_index": 1,
                                        "success_status": "Prompt Injection Successful",
                                    },
                                ],
                            },
                        },
                    },
                ],
            },
        ],
    )[0]

    assert summary["safe"] == 1
    assert summary["unsafe"] == 1
    assert summary["unknown"] == 0
    assert summary["acceptable_rate"] == 50


def test_running_job_reads_live_prompt_progress_from_runner_database(tmp_path, monkeypatch) -> None:
    output_dir = tmp_path / "generated-outputs"
    database_dir = output_dir / "databases"
    database_dir.mkdir(parents=True)
    monkeypatch.setattr(job_store, "MOONSHOT_OUTPUT_DIR", output_dir)

    store = JobStore(job_dir=tmp_path / "jobs")
    request = BenchmarkRecipeRequest(
        run_name="live-progress",
        endpoints=["endpoint"],
        recipes=["recipe"],
        estimated_prompts=10,
    )
    created = store.create_job(request)
    store.mark_started(created["id"], created["runner_id"])

    database_file = database_dir / f"{created['runner_id']}.db"
    with sqlite3.connect(database_file) as connection:
        connection.execute("create table runner_cache_table (id integer primary key)")
        connection.executemany(
            "insert into runner_cache_table default values",
            [() for _ in range(4)],
        )

    running = store.enrich_job(store.get(created["id"]), include_interactions=False)

    assert running["summary"]["completed_prompts"] == 4
    assert running["progress"] == 40
    assert running["summary"]["judge_progress"]["phase"] == "pending"

    with sqlite3.connect(database_file) as connection:
        connection.executemany(
            "insert into runner_cache_table default values",
            [() for _ in range(6)],
        )

    evaluating = store.enrich_job(store.get(created["id"]), include_interactions=False)

    assert evaluating["summary"]["completed_prompts"] == 10
    assert evaluating["progress"] == 95
    assert evaluating["summary"]["judge_progress"] == {
        "phase": "evaluating",
        "completed": 0,
        "total": 10,
        "percentage": 0,
    }
