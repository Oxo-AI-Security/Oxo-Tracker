from __future__ import annotations

from pathlib import Path

import pytest

from app.services.task_agent_benchmark import (
    BenchmarkManifestError,
    benchmark_report,
    load_benchmark_manifest,
    run_controlled_benchmark,
)


MANIFEST_PATH = (
    Path(__file__).parent
    / "fixtures"
    / "task_agent_benchmark_manifest.json"
)


def test_controlled_manifest_has_20_fixed_cases_and_four_intensities() -> None:
    manifest = load_benchmark_manifest(MANIFEST_PATH)

    assert len(manifest["cases"]) == 20
    assert manifest["repetitions"] == 3
    assert manifest["expected_run_count"] == 240
    assert set(manifest["exploration_intensities"]) == {
        "light",
        "standard",
        "deep",
        "extreme",
    }
    assert len({item["case_id"] for item in manifest["cases"]}) == 20
    assert len({item["target_id"] for item in manifest["cases"]}) == 20


def test_benchmark_runs_every_cell_and_reports_required_p0_metrics() -> None:
    manifest = load_benchmark_manifest(MANIFEST_PATH)

    def runner(case: dict, intensity: str, repetition: int) -> dict:
        expected = bool(case["expected_goal_complete"])
        effort = {
            "light": 1,
            "standard": 2,
            "deep": 3,
            "extreme": 4,
        }[intensity]
        return {
            "predicted_goal_complete": expected,
            "actual_goal_achieved": expected,
            "duration_seconds": effort + repetition / 10,
            "estimated_cost": effort * 0.01,
            "input_tokens": effort * 100,
            "output_tokens": effort * 20,
            "rounds": effort,
        }

    records, report = run_controlled_benchmark(manifest, runner)

    assert len(records) == 240
    assert report["case_count"] == 20
    assert report["run_count"] == 240
    assert report["overall"]["goal_complete_precision"] == 1
    assert report["overall"]["goal_complete_recall"] == 1
    assert report["overall"]["crash_rate"] == 0
    assert report["overall"]["asr"] == 0.5
    assert report["overall"]["asr_confidence_95"]["low"] < 0.5
    assert report["overall"]["asr_confidence_95"]["high"] > 0.5
    assert report["overall"]["duration_seconds"]["p95"] > 0
    assert report["overall"]["estimated_cost"]["total"] > 0
    assert set(report["by_intensity"]) == {
        "light",
        "standard",
        "deep",
        "extreme",
    }


def test_runner_crashes_are_isolated_and_measured() -> None:
    manifest = load_benchmark_manifest(MANIFEST_PATH)

    def runner(case: dict, intensity: str, repetition: int) -> dict:
        if (
            case["case_id"] == "secret-direct-vulnerable"
            and intensity == "light"
            and repetition == 1
        ):
            raise RuntimeError("controlled crash")
        expected = bool(case["expected_goal_complete"])
        return {
            "predicted_goal_complete": expected,
            "actual_goal_achieved": expected,
        }

    records, report = run_controlled_benchmark(manifest, runner)

    assert sum(bool(item["crashed"]) for item in records) == 1
    assert report["overall"]["crash_rate"] == round(1 / 240, 6)
    assert report["overall"]["crash_rate_confidence_95"]["high"] > 0


def test_report_rejects_missing_or_duplicate_cells() -> None:
    manifest = load_benchmark_manifest(MANIFEST_PATH)

    with pytest.raises(BenchmarkManifestError, match="incomplete"):
        benchmark_report(manifest, [])
