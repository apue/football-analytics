"""Stable business-result comparison for academy analysis outputs."""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def verify_analysis_baseline(
    analysis_dir: Path, coverage_path: Path, baseline_path: Path
) -> dict[str, Any]:
    """Compare normalized analysis counts with a frozen version-one baseline."""

    baseline = _load_object(baseline_path)
    if baseline.get("schema_version") != 1:
        raise ValueError("baseline schema_version must be 1")
    validation = _load_object(analysis_dir / "validation.json")
    if validation.get("valid") is not True:
        raise ValueError("analysis validation must pass before baseline comparison")

    cohorts = _read_csv(analysis_dir / "exit_cohorts.csv")
    outcomes = _read_csv(analysis_dir / "player_threshold_outcomes.csv")
    coverage = _read_csv(coverage_path)
    actual = _actual_summary(cohorts, outcomes, coverage)
    expected = {
        "player_count": baseline.get("player_count"),
        "exit_cohorts": baseline.get("exit_cohorts"),
        "coverage": baseline.get("coverage"),
        "thresholds": baseline.get("thresholds"),
    }
    differences = [key for key in expected if actual.get(key) != expected.get(key)]
    return {
        "valid": not differences,
        "differences": differences,
        "expected": expected,
        "actual": actual,
    }


def _actual_summary(
    cohorts: list[dict[str, str]],
    outcomes: list[dict[str, str]],
    coverage: list[dict[str, str]],
) -> dict[str, Any]:
    exit_counts = Counter(row["exit_season_start"] for row in cohorts)
    coverage_counts = Counter(row["status"] for row in coverage)
    by_threshold: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in outcomes:
        by_threshold[row["threshold"]].append(row)
    thresholds = {}
    for threshold, rows in sorted(by_threshold.items(), key=lambda item: int(item[0])):
        thresholds[threshold] = {
            "established": sum(row["status"] == "reached" for row in rows),
            "sustained": sum(row["sustained_status"] == "reached" for row in rows),
            "unknown": sum(row["status"] == "unknown" for row in rows),
        }
    return {
        "player_count": len(cohorts),
        "exit_cohorts": dict(sorted(exit_counts.items())),
        "coverage": {
            "total": len(coverage),
            "complete": coverage_counts["complete"],
            "partial": coverage_counts["partial"],
            "missing": coverage_counts["missing"],
        },
        "thresholds": thresholds,
    }


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))
