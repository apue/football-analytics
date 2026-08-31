"""Validated offline orchestration for academy-conversion analysis."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .academy_conversion import (
    RosterMembership,
    build_exit_cohorts,
    calculate_player_outcomes,
    summarize_outcomes,
    validate_research_rows,
)
from .academy_conversion_io import (
    load_appearances,
    load_competition_rules,
    load_coverage,
    load_roster_memberships,
    write_analysis_artifacts,
)
from .academy_sources import require_source_evidence
from .academy_study import AcademyStudyConfig, load_academy_study_config
from .evidence_bundle import canonicalize_url


def run_academy_analysis(
    *,
    study_config_path: Path,
    rosters_path: Path,
    appearances_path: Path,
    competitions_path: Path,
    coverage_path: Path,
    output_dir: Path,
) -> dict[str, int | bool]:
    """Validate frozen inputs, calculate outcomes, and write analysis artifacts."""

    study = load_academy_study_config(study_config_path)
    _require_within(output_dir, Path(study.run_dir), "output directory")
    source_config = require_source_evidence(
        Path(study.roster_source_config_path), Path(study.roster_evidence_path)
    )
    memberships = load_roster_memberships(rosters_path)
    _validate_memberships_for_study(memberships, study, source_config)
    appearances = load_appearances(appearances_path)
    rules = load_competition_rules(competitions_path)
    coverage = load_coverage(coverage_path)

    actual_scope_ids = {row.scope_id for row in coverage}
    if actual_scope_ids != {study.adult_source_scope_id}:
        raise ValueError(
            "coverage facts do not match study adult-source scope: "
            f"expected={study.adult_source_scope_id}, actual={sorted(actual_scope_ids)}"
        )
    policy = _load_object(Path(study.competition_policy_path))
    policy_version = str(policy.get("policy_version", ""))
    actual_policy_versions = {row.policy_version for row in rules}
    if actual_policy_versions != {policy_version}:
        raise ValueError(
            "competition facts do not match study policy: "
            f"expected={policy_version}, actual={sorted(actual_policy_versions)}"
        )

    issues = validate_research_rows(memberships, appearances, rules, coverage)
    cohorts = build_exit_cohorts(
        memberships,
        exit_start=study.exit_season_start,
        exit_end=study.exit_season_end,
    )
    outcomes = []
    summary = []
    if not issues:
        outcomes = calculate_player_outcomes(
            cohorts,
            appearances,
            rules,
            coverage,
            thresholds=study.sensitivity_thresholds,
            observation_season_count=study.observation_season_count,
            sustained_qualifying_seasons=study.sustained_qualifying_seasons,
        )
        summary = summarize_outcomes(outcomes, thresholds=study.sensitivity_thresholds)
    write_analysis_artifacts(
        output_dir,
        cohorts,
        outcomes,
        summary,
        issues,
        thresholds=study.sensitivity_thresholds,
        provenance={
            "input_artifacts": {
                "rosters": str(rosters_path),
                "appearances": str(appearances_path),
                "competitions": str(competitions_path),
                "coverage": str(coverage_path),
            },
            "roster_source_urls": sorted({row.source_url for row in memberships}),
            "appearance_source_urls": sorted({row.source_url for row in appearances}),
            "coverage_source_urls": sorted({row.source_url for row in coverage}),
            "policy_versions": sorted(actual_policy_versions),
            "adult_source_scope_id": study.adult_source_scope_id,
            "study_config": str(study_config_path),
            "study": study.summary(),
        },
    )
    return {
        "valid": not issues,
        "issue_count": len(issues),
        "player_count": len(cohorts),
    }


def _validate_memberships_for_study(
    memberships: Sequence[RosterMembership],
    study: AcademyStudyConfig,
    source_config: Mapping[str, Any],
) -> None:
    academies = {row.academy_id for row in memberships}
    if academies != {study.academy_id}:
        raise ValueError(
            "roster facts do not match study academy: "
            f"expected={study.academy_id}, actual={sorted(academies)}"
        )
    expected_seasons = set(
        range(study.roster_season_start, study.roster_season_end + 1)
    )
    actual_seasons = {row.season_start for row in memberships}
    if actual_seasons != expected_seasons:
        raise ValueError(
            "roster facts do not cover configured seasons: "
            f"expected={sorted(expected_seasons)}, actual={sorted(actual_seasons)}"
        )
    if source_config.get("academy_id") != study.academy_id:
        raise ValueError("roster source academy does not match study")

    expected_counts: Counter[int] = Counter()
    expected_urls: set[str] = set()
    for page in source_config["pages"]:
        try:
            season = int(page["season_start"])
            count = int(page["expected_player_count"])
            source_url = canonicalize_url(str(page["url"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "roster source pages require season_start and expected_player_count"
            ) from exc
        if count < 1:
            raise ValueError("expected_player_count must be positive")
        expected_counts[season] += count
        expected_urls.add(source_url)
    actual_counts = Counter(row.season_start for row in memberships)
    if actual_counts != expected_counts:
        raise ValueError(
            "roster fact counts do not match source contract: "
            f"expected={dict(expected_counts)}, actual={dict(actual_counts)}"
        )
    actual_urls = {canonicalize_url(row.source_url) for row in memberships}
    if actual_urls != expected_urls:
        raise ValueError("roster fact URLs do not match approved source evidence")


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _require_within(path: Path, parent: Path, label: str) -> None:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must be inside configured run directory") from exc
