from __future__ import annotations

import math
import statistics
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any


SUPPORTED_INTENSITIES = ("light", "standard", "deep", "extreme")


class BenchmarkManifestError(ValueError):
    pass


def load_benchmark_manifest(path: Path) -> dict[str, Any]:
    import json

    manifest = json.loads(path.read_text(encoding="utf-8"))
    return validate_benchmark_manifest(manifest)


def validate_benchmark_manifest(
    source: dict[str, Any],
) -> dict[str, Any]:
    manifest = dict(source)
    cases = list(manifest.get("cases") or [])
    repetitions = int(manifest.get("repetitions") or 0)
    intensities = list(manifest.get("exploration_intensities") or [])
    if int(manifest.get("schema_version") or 0) != 1:
        raise BenchmarkManifestError("Unsupported benchmark schema version.")
    if len(cases) < 20:
        raise BenchmarkManifestError(
            "A controlled P0 benchmark requires at least 20 fixed cases."
        )
    if repetitions < 3 or repetitions > 5:
        raise BenchmarkManifestError(
            "Each benchmark configuration must repeat three to five times."
        )
    if set(intensities) != set(SUPPORTED_INTENSITIES):
        raise BenchmarkManifestError(
            "The benchmark must cover every exploration intensity exactly once."
        )
    seen: set[str] = set()
    normalized_cases: list[dict[str, Any]] = []
    for raw in cases:
        case = dict(raw or {})
        case_id = str(case.get("case_id") or "").strip()
        target_id = str(case.get("target_id") or "").strip()
        goal = str(case.get("goal") or "").strip()
        if not case_id or case_id in seen:
            raise BenchmarkManifestError(
                "Benchmark case IDs must be non-empty and unique."
            )
        if not target_id or not goal:
            raise BenchmarkManifestError(
                f"Benchmark case {case_id} requires a fixed target and goal."
            )
        if not isinstance(case.get("expected_goal_complete"), bool):
            raise BenchmarkManifestError(
                f"Benchmark case {case_id} requires a boolean oracle."
            )
        seen.add(case_id)
        normalized_cases.append(case)
    return {
        **manifest,
        "repetitions": repetitions,
        "exploration_intensities": list(SUPPORTED_INTENSITIES),
        "cases": normalized_cases,
        "expected_run_count": (
            len(normalized_cases)
            * len(SUPPORTED_INTENSITIES)
            * repetitions
        ),
    }


def run_controlled_benchmark(
    manifest: dict[str, Any],
    runner: Callable[[dict[str, Any], str, int], dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Execute every fixed case/intensity/repetition with crash isolation."""

    checked = validate_benchmark_manifest(manifest)
    records: list[dict[str, Any]] = []
    for case in checked["cases"]:
        for intensity in checked["exploration_intensities"]:
            for repetition in range(1, checked["repetitions"] + 1):
                started = time.perf_counter()
                try:
                    output = dict(runner(case, intensity, repetition) or {})
                    crashed = False
                    error = None
                except Exception as exception:
                    output = {}
                    crashed = True
                    error = str(exception)[:1_000]
                duration = max(
                    0.0,
                    float(
                        output.get("duration_seconds")
                        or (time.perf_counter() - started)
                    ),
                )
                records.append(
                    {
                        "case_id": case["case_id"],
                        "target_id": case["target_id"],
                        "goal": case["goal"],
                        "intensity": intensity,
                        "repetition": repetition,
                        "expected_goal_complete": bool(
                            case["expected_goal_complete"]
                        ),
                        "predicted_goal_complete": bool(
                            output.get("predicted_goal_complete", False)
                        ),
                        "actual_goal_achieved": bool(
                            output.get("actual_goal_achieved", False)
                        ),
                        "crashed": crashed
                        or bool(output.get("crashed", False)),
                        "duration_seconds": duration,
                        "estimated_cost": max(
                            0.0,
                            float(output.get("estimated_cost") or 0.0),
                        ),
                        "input_tokens": max(
                            0,
                            int(output.get("input_tokens") or 0),
                        ),
                        "output_tokens": max(
                            0,
                            int(output.get("output_tokens") or 0),
                        ),
                        "rounds": max(0, int(output.get("rounds") or 0)),
                        "error": error or output.get("error"),
                    }
                )
    return records, benchmark_report(checked, records)


def benchmark_report(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    checked = validate_benchmark_manifest(manifest)
    expected_keys = {
        (case["case_id"], intensity, repetition)
        for case in checked["cases"]
        for intensity in checked["exploration_intensities"]
        for repetition in range(1, checked["repetitions"] + 1)
    }
    actual_keys = {
        (
            str(item.get("case_id") or ""),
            str(item.get("intensity") or ""),
            int(item.get("repetition") or 0),
        )
        for item in records
    }
    if actual_keys != expected_keys or len(records) != len(expected_keys):
        missing = sorted(expected_keys - actual_keys)[:10]
        extra = sorted(actual_keys - expected_keys)[:10]
        raise BenchmarkManifestError(
            f"Benchmark records are incomplete or duplicated; "
            f"missing={missing}, extra={extra}."
        )
    overall = _metric_slice(records)
    by_intensity = {
        intensity: _metric_slice(
            [
                item
                for item in records
                if str(item.get("intensity") or "") == intensity
            ]
        )
        for intensity in checked["exploration_intensities"]
    }
    return {
        "schema_version": 1,
        "manifest_id": checked.get("manifest_id"),
        "case_count": len(checked["cases"]),
        "run_count": len(records),
        "repetitions": checked["repetitions"],
        "overall": overall,
        "by_intensity": by_intensity,
    }


def _metric_slice(records: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(records)
    predicted = [
        bool(item.get("predicted_goal_complete")) for item in records
    ]
    expected = [bool(item.get("expected_goal_complete")) for item in records]
    achieved = [bool(item.get("actual_goal_achieved")) for item in records]
    crashed = [bool(item.get("crashed")) for item in records]
    true_positive = sum(p and e for p, e in zip(predicted, expected))
    false_positive = sum(p and not e for p, e in zip(predicted, expected))
    false_negative = sum(not p and e for p, e in zip(predicted, expected))
    true_negative = total - true_positive - false_positive - false_negative
    precision = _safe_ratio(true_positive, true_positive + false_positive)
    recall = _safe_ratio(true_positive, true_positive + false_negative)
    asr_count = sum(achieved)
    crash_count = sum(crashed)
    durations = [float(item.get("duration_seconds") or 0) for item in records]
    costs = [float(item.get("estimated_cost") or 0) for item in records]
    input_tokens = [int(item.get("input_tokens") or 0) for item in records]
    output_tokens = [int(item.get("output_tokens") or 0) for item in records]
    rounds = [int(item.get("rounds") or 0) for item in records]
    return {
        "runs": total,
        "asr": _safe_ratio(asr_count, total),
        "asr_confidence_95": _wilson_interval(asr_count, total),
        "goal_complete_precision": precision,
        "goal_complete_recall": recall,
        "confusion_matrix": {
            "true_positive": true_positive,
            "true_negative": true_negative,
            "false_positive": false_positive,
            "false_negative": false_negative,
        },
        "crash_rate": _safe_ratio(crash_count, total),
        "crash_rate_confidence_95": _wilson_interval(crash_count, total),
        "duration_seconds": _distribution(durations),
        "estimated_cost": _distribution(costs),
        "input_tokens": _distribution(input_tokens),
        "output_tokens": _distribution(output_tokens),
        "rounds": _distribution(rounds),
    }


def _distribution(values: list[float | int]) -> dict[str, float]:
    numbers = sorted(float(value) for value in values)
    if not numbers:
        return {"mean": 0.0, "median": 0.0, "p95": 0.0, "total": 0.0}
    return {
        "mean": round(statistics.fmean(numbers), 6),
        "median": round(statistics.median(numbers), 6),
        "p95": round(_percentile(numbers, 0.95), 6),
        "total": round(sum(numbers), 6),
    }


def _percentile(values: list[float], fraction: float) -> float:
    if len(values) == 1:
        return values[0]
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _safe_ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _wilson_interval(successes: int, total: int) -> dict[str, float]:
    if total <= 0:
        return {"low": 0.0, "high": 0.0}
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    center = (proportion + z * z / (2 * total)) / denominator
    margin = (
        z
        * math.sqrt(
            proportion * (1 - proportion) / total
            + z * z / (4 * total * total)
        )
        / denominator
    )
    return {
        "low": round(max(0.0, center - margin), 6),
        "high": round(min(1.0, center + margin), 6),
    }
